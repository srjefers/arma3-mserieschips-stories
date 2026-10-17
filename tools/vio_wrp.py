#!/usr/bin/env python3
"""vio_wrp.py — alturas, pendientes y caminos de un mapa de Arma 3, leídos del PBO del terreno. Solo lectura.

  - Alturas: la grilla de elevación del .wrp (OPRW v24/v25), descomprimida con LZO1X en Python puro.
    La grilla va de sur a norte: el vértice (i, j) está en x = i*g, y = j*g, con g = tamaño del mapa / ancho.
    Entre vértices se interpola bilinealmente. El revisor del diseño lo comparó con CW Takistán:
    mediana 0.00 m y máximo 0.04 m sobre 378 pueblos, campamentos y puntos.
  - Caminos: roads.shp del mismo PBO, si existe; a veces trae un desfase de +200000 m en x, que se quita.
Solo lee la cabecera del PBO y los bytes del .wrp que necesita (el PBO de Krayina pesa más de 300 MB).

Uso directo:  vio_wrp.py <pbo del terreno> [x,y ...]   (tamaño del mapa, rango de alturas y altura/pendiente en esos puntos)
"""
import os
import struct
import sys
import time

import numpy as np


# ---------------------------------------------------------------- PBO (solo cabecera + una entrada)

def pbo_entries(path):
    """[(nombre, offset de datos, tamaño, comprimida)] leyendo solo la cabecera del PBO."""
    with open(path, "rb") as f:
        buf = bytearray()
        pos = 0

        def need(n):
            while len(buf) < pos + n:
                chunk = f.read(1 << 20)
                if not chunk:
                    raise ValueError(f"{path}: cabecera truncada")
                buf.extend(chunk)

        def asciiz():
            nonlocal pos
            while True:
                end = buf.find(b"\0", pos)
                if end >= 0:
                    break
                chunk = f.read(1 << 20)
                if not chunk:
                    raise ValueError(f"{path}: cabecera truncada")
                buf.extend(chunk)
            s = buf[pos:end].decode("latin-1")
            pos = end + 1
            return s

        entries = []
        first = True
        while True:
            name = asciiz()
            need(20)
            method, orig, _res, _ts, size = struct.unpack_from("<5I", buf, pos)
            pos += 20
            if name == "" and method == 0x56657273 and first:   # 'Vers' + propiedades
                while asciiz() != "":
                    asciiz()
                first = False
                continue
            first = False
            if name == "":
                break
            entries.append([name, 0, size, method == 0x43707273 or orig not in (0, size)])
        off = pos
        for e in entries:
            e[1] = off
            off += e[2]
    return [tuple(e) for e in entries]


def read_entry(path, suffix, limit=None):
    """Bytes de la primera entrada cuyo nombre termina en `suffix` (sin distinguir mayúsculas)."""
    for name, off, size, comp in pbo_entries(path):
        if name.lower().endswith(suffix.lower()):
            if comp:
                raise ValueError(f"{path}: {name} está comprimida (no soportado)")
            with open(path, "rb") as f:
                f.seek(off)
                return name, f.read(size if limit is None else min(size, limit))
    return None, None


# ---------------------------------------------------------------- LZO1X (Python puro)

def lzo1x(src, ip, out_len):
    """Descomprime un flujo LZO1X que empieza en src[ip]. Devuelve (bytes, posición final)."""
    dst = bytearray()

    def copy_match(m_pos, n):
        if m_pos < 0:
            raise ValueError("LZO: referencia hacia atrás inválida")
        if m_pos + n <= len(dst):
            dst.extend(dst[m_pos:m_pos + n])
        else:
            for k in range(n):
                dst.append(dst[m_pos + k])

    state = 0   # 0 = espera un byte de literales, 1 = tras la primera tanda de literales, 2 = coincidencia con t ya leído
    t = src[ip]
    if t > 17:
        t -= 17
        ip += 1
        dst.extend(src[ip:ip + t])
        ip += t
        if t < 4:
            t = src[ip]
            ip += 1
            state = 2
        else:
            state = 1
    while len(dst) < out_len:
        if state == 0:
            t = src[ip]
            ip += 1
            if t >= 16:
                state = 2
            else:
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 15 + src[ip]
                    ip += 1
                n = t + 3
                dst.extend(src[ip:ip + n])
                ip += n
                state = 1
            continue
        if state == 1:
            t = src[ip]
            ip += 1
            if t >= 16:
                state = 2
                continue
            m_pos = len(dst) - (1 + 0x0800) - (t >> 2) - (src[ip] << 2)
            ip += 1
            copy_match(m_pos, 3)
        else:
            if t >= 64:
                m_pos = len(dst) - 1 - ((t >> 2) & 7) - (src[ip] << 3)
                ip += 1
                copy_match(m_pos, (t >> 5) + 1)
            elif t >= 32:
                t &= 31
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 31 + src[ip]
                    ip += 1
                m_pos = len(dst) - 1 - ((src[ip] >> 2) + (src[ip + 1] << 6))
                ip += 2
                copy_match(m_pos, t + 2)
            elif t >= 16:
                m_pos = len(dst) - ((t & 8) << 11)
                t &= 7
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 7 + src[ip]
                    ip += 1
                m_pos -= (src[ip] >> 2) + (src[ip + 1] << 6)
                ip += 2
                if m_pos == len(dst):
                    return bytes(dst), ip   # marca de fin
                m_pos -= 0x4000
                copy_match(m_pos, t + 2)
            else:
                m_pos = len(dst) - 1 - (t >> 2) - (src[ip] << 2)
                ip += 1
                copy_match(m_pos, 2)
        t = src[ip - 2] & 3
        if t == 0:
            state = 0
        else:
            dst.extend(src[ip:ip + t])
            ip += t
            t = src[ip]
            ip += 1
            state = 2
    if src[ip:ip + 3] == b"\x11\x00\x00":
        ip += 3
    return bytes(dst[:out_len]), ip


def _compressed(b, p, nbytes):
    if nbytes < 1024:
        return b[p:p + nbytes], p + nbytes
    return lzo1x(b, p, nbytes)


def _skip_quadtree(b, p):
    flag = b[p]
    p += 1
    if not flag:
        return p + 4

    def node(p):
        mask = struct.unpack_from("<H", b, p)[0]
        p += 2
        for i in range(16):
            p = node(p) if mask & (1 << i) else p + 4
        return p
    return node(p)


# ---------------------------------------------------------------- terreno

class Terrain:
    def __init__(self, elev, world_size, roads=None, source=""):
        self.e = elev
        self.ty, self.tx = elev.shape
        self.size = float(world_size)
        self.g = self.size / self.tx
        self.segs = roads if roads is not None else np.zeros((0, 4))
        self.source = source

    def h(self, x, y):
        """Altura sobre el nivel del mar (bilineal); acepta números o arreglos."""
        fx = np.clip(np.asarray(x, dtype=float) / self.g, 0, self.tx - 1.000001)
        fy = np.clip(np.asarray(y, dtype=float) / self.g, 0, self.ty - 1.000001)
        i0 = np.floor(fx).astype(int)
        j0 = np.floor(fy).astype(int)
        t, u = fx - i0, fy - j0
        e = self.e
        return ((1 - t) * (1 - u) * e[j0, i0] + t * (1 - u) * e[j0, i0 + 1]
                + (1 - t) * u * e[j0 + 1, i0] + t * u * e[j0 + 1, i0 + 1])

    def slope(self, x, y, r=10.0):
        """Pendiente (fracción: 0.10 = 10 %) por diferencias centrales a ±r metros."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        sx = (self.h(x + r, y) - self.h(x - r, y)) / (2 * r)
        sy = (self.h(x, y + r) - self.h(x, y - r)) / (2 * r)
        return np.hypot(sx, sy)

    def disc(self, x, y, radius, step):
        """Puntos de una grilla dentro de un círculo (para medir agua o pendiente alrededor)."""
        k = int(radius // step)
        d = np.arange(-k, k + 1) * step
        dx, dy = np.meshgrid(d, d)
        m = dx * dx + dy * dy <= radius * radius
        return x + dx[m], y + dy[m]

    def slope_stats(self, x, y, radius, step=10.0):
        """(p90, máximo) de la pendiente dentro del radio."""
        px, py = self.disc(x, y, radius, step)
        s = self.slope(px, py)
        return float(np.percentile(s, 90)), float(s.max())

    def wet_share(self, x, y, radius, step=20.0, level=0.3):
        """Fracción de puntos con agua (altura <= level) dentro del radio."""
        px, py = self.disc(x, y, radius, step)
        return float((self.h(px, py) <= level).mean())

    def min_h(self, x, y, half):
        """Altura mínima en un cuadrado de lado 2*half (huella de una construcción)."""
        d = np.array([-half, 0, half])
        dx, dy = np.meshgrid(d, d)
        return float(self.h(x + dx.ravel(), y + dy.ravel()).min())

    def road_dist(self, x, y):
        """Distancia al eje de camino más cercano (inf si el mapa no trae caminos)."""
        if len(self.segs) == 0:
            return np.full(np.shape(x), np.inf) if np.ndim(x) else float("inf")
        px = np.atleast_1d(np.asarray(x, dtype=float))[:, None]
        py = np.atleast_1d(np.asarray(y, dtype=float))[:, None]
        x1, y1, x2, y2 = (self.segs[:, k][None, :] for k in range(4))
        vx, vy = x2 - x1, y2 - y1
        L2 = vx * vx + vy * vy
        L2[L2 == 0] = 1e-9
        t = np.clip(((px - x1) * vx + (py - y1) * vy) / L2, 0, 1)
        d = np.hypot(px - (x1 + t * vx), py - (y1 + t * vy)).min(axis=1)
        return d if np.ndim(x) else float(d[0])


def _roads_from_shp(data):
    if not data or len(data) < 100:
        return np.zeros((0, 4))
    bbox = struct.unpack_from("<4d", data, 36)
    off = 200000.0 if bbox[0] > 100000 else 0.0
    p, segs = 100, []
    while p + 8 <= len(data):
        _rn, clen = struct.unpack_from(">2i", data, p)
        p += 8
        rec = data[p:p + clen * 2]
        p += clen * 2
        if len(rec) < 44 or struct.unpack_from("<i", rec, 0)[0] not in (3, 13, 23):
            continue
        nparts, npts = struct.unpack_from("<2i", rec, 36)
        parts = list(struct.unpack_from("<%di" % nparts, rec, 44)) + [npts]
        pts = np.frombuffer(rec, "<f8", npts * 2, 44 + 4 * nparts).reshape(npts, 2).copy()
        pts[:, 0] -= off
        for i in range(nparts):
            seg = pts[parts[i]:parts[i + 1]]
            if len(seg) >= 2:
                segs.append(np.hstack([seg[:-1], seg[1:]]))
    return np.vstack(segs) if segs else np.zeros((0, 4))


def load(pbo_path, verbose=False):
    """Terrain con alturas (y caminos si hay roads.shp) del PBO del terreno."""
    t0 = time.time()
    name, b = read_entry(pbo_path, ".wrp", limit=200 << 20)
    if b is None:
        raise ValueError(f"{pbo_path}: no trae .wrp")
    if b[:4] != b"OPRW":
        raise ValueError(f"{name}: no es OPRW")
    ver = struct.unpack_from("<I", b, 4)[0]
    p = 12 if ver >= 25 else 8
    lx, _ly, tx, ty = struct.unpack_from("<4I", b, p)
    p += 16
    cell = struct.unpack_from("<f", b, p)[0]
    p += 4
    p = _skip_quadtree(b, p)                      # geografía
    p = _skip_quadtree(b, p)                      # sonido
    npk = struct.unpack_from("<I", b, p)[0]
    p += 4 + 12 * npk                              # cumbres
    p = _skip_quadtree(b, p)                      # índices de materiales
    _, p = _compressed(b, p, tx * ty)             # clutter aleatorio
    _, p = _compressed(b, p, tx * ty)             # segundo arreglo de bytes
    raw, p = _compressed(b, p, tx * ty * 4)       # elevaciones (float32)
    elev = np.frombuffer(raw, "<f4").reshape(ty, tx).astype(np.float32)
    _, shp = read_entry(pbo_path, "roads.shp")
    terr = Terrain(elev, lx * cell, _roads_from_shp(shp), source=f"{os.path.basename(pbo_path)}:{name}")
    if verbose:
        print(f"{terr.source}: OPRW v{ver}, mapa {terr.size:.0f} m, grilla {tx}x{ty} (g={terr.g:.2f} m), "
              f"alturas {elev.min():.1f} a {elev.max():.1f} m, {len(terr.segs)} tramos de camino, {time.time() - t0:.1f} s")
    return terr


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    T = load(sys.argv[1], verbose=True)
    for xy in sys.argv[2:]:
        x, y = map(float, xy.split(","))
        print(f"  ({x:.0f},{y:.0f}): h={float(T.h(x, y)):.2f} m  pendiente={float(T.slope(x, y)) * 100:.1f} %  "
              f"camino a {float(T.road_dist(x, y)):.0f} m")
