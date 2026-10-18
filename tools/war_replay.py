#!/usr/bin/env python3
"""war_replay.py - "Historia de la guerra" (parche war_replay de VIO-BECTI-CW): lista y exporta las partidas grabadas.

Lee el perfil del anfitrion (<perfil>.vars.Arma3Profile, archivo "rapificado" que empieza con "\\0raP"; SOLO LECTURA)
o un texto copiado en el juego (copyToClipboard str VIOC_WR_DATA), y exporta:
  - un HTML autocontenido (mapa del terreno embebido en base64, pueblos y zonas por duenio en el tiempo, equipos,
    reproducir/pausa, velocidad, barra de tiempo, avisos, pueblos por bando y grafica de pueblos por bando);
  - un GIF animado (Pillow; sin ffmpeg).
Solo biblioteca estandar + Pillow. El subcomando "basemap" (pinta y guarda el mapa de un terreno) usa ademas numpy y
tools/vio_wrp.py del proyecto (alturas, caminos y casas del PBO del terreno; solo lectura).

Uso:
  war_replay.py list   [--profile P | --sqf F]                     partidas grabadas (en curso y las 3 ultimas terminadas)
  war_replay.py export [--profile P | --sqf F] [--game N] [--html OUT.html] [--gif OUT.gif]
                       [--seconds 60] [--gif-seconds 24] [--fps 10] [--gif-size 720] [--maps DIR] [--names "A,B,C"]
  war_replay.py basemap --world Tanoa [--pbo terreno.pbo] [--size 2048] [--maps DIR]
  war_replay.py sample [--out sample.vars.Arma3Profile] [--seed 7]  perfil sintetico (mismo formato que el del juego)
  war_replay.py selftest [--profile P]                             ida y vuelta del formato + lectura del perfil real
  war_replay.py dump   [--profile P] [--grep vioc]                 variables del perfil (nombre, tipo, tamanio)
Por defecto: el perfil (.vars.Arma3Profile) modificado mas recientemente en ~/Library/Application Support/com.vpltd.Arma3/
GameDocuments (o $WAR_REPLAY_PROFILE),
mapas en <carpeta de este script>/war_replay_maps (o $WAR_REPLAY_MAPS). Si se mueve el script a tools/, mover tambien
war_replay_maps/.

Formato del registro (VIOCWR1, lo escribe VIOC_war_replay.sqf):
  [ "VIOCWR1", meta, pueblos, cambios, avisos, fotos, estado ]
  meta    = [missionName, worldName, worldSize, briefingName, systemTime al empezar [a,m,d,h,min,s,ms], date al empezar
             [a,m,d,h,min], [nombre oeste, nombre este, nombre resistencia], version, unidad (10 m)]
  pueblos = [[nombre, x, y, duenio inicial, marcas (1 capital, 2 aerodromo)], ...]   (metros)
  cambios = "t,pueblo,bando;..."            (t en s de partida; bando 0 oeste, 1 este, 2 resistencia, otro = sin duenio)
  avisos  = "t,tipo,bando,x,y,dato;..."     (x, y en unidades; tipos start resume cap af hq base so cas gs end)
  fotos   = "t,minuto del dia,OESTE,ESTE;..." (OESTE/ESTE = "x y x y ..." en unidades, o "-")
  estado  = [t final, terminada 0/1, ganador, systemTime final, date final, posiciones, cambios, avisos, recortes,
             intervalo de fotos]
Perfil: variable "VIOC_WAR_<mision>_<mundo>" (el juego la guarda en minusculas) = partida en curso; "..._HIST" = lista de
las ultimas partidas terminadas (o cortadas). En el .vars.Arma3Profile cada variable es class ItemN {name; class data
{singleType = "SCALAR"/"STRING"/"BOOL"/"ARRAY"...; value = ... o class value {items = n; class Item0 {class data ...}}}};
los numeros se guardan como float de 32 bits (por eso las posiciones y los tiempos van como texto o enteros).
"""
import argparse
import base64
import datetime
import glob
import io
import json
import math
import os
import random
import re
import struct
import sys

sys.dont_write_bytecode = True  # no escribir __pycache__ en tools/ al importar vio_wrp

HERE = os.path.dirname(os.path.abspath(__file__))
MAPS_DIR = os.environ.get("WAR_REPLAY_MAPS") or os.path.join(HERE, "war_replay_maps")
GAMEDOCS = os.path.expanduser("~/Library/Application Support/com.vpltd.Arma3/GameDocuments/Arma 3")


def _find_profile():
    """El .vars.Arma3Profile modificado mas recientemente (perfil principal u 'Other Profiles'); $WAR_REPLAY_PROFILE manda."""
    if os.environ.get("WAR_REPLAY_PROFILE"):
        return os.environ["WAR_REPLAY_PROFILE"]
    pats = [os.path.join(GAMEDOCS, "*.vars.Arma3Profile"),
            os.path.join(os.path.dirname(GAMEDOCS), "Arma 3 - Other Profiles", "*", "*.vars.Arma3Profile")]
    found = [f for pat in pats for f in glob.glob(pat)]
    return max(found, key=os.path.getmtime) if found else os.path.join(GAMEDOCS, "<perfil>.vars.Arma3Profile")


DEFAULT_PROFILE = _find_profile()
ARMA = os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Arma 3")
WORKSHOP = os.path.expanduser("~/Library/Application Support/Steam/steamapps/workshop/content/107410")
TAG = "VIOCWR1"
KEY_PREFIX = "vioc_war_"
# Colores de los bandos (validados para daltonismo con la guia dataviz: azul, rojo-naranja, verde agua; gris neutro)
SIDE_HEX = ["#3987e5", "#e0503a", "#199e70", "#8d8c86"]
SIDE_DEFAULT_NAMES = ["Oeste", "Este", "Guerrilla"]
# PBO del terreno por mundo (relativo a la carpeta del juego) para "basemap"
WORLD_PBO = {
    "tanoa": "Expansion/Addons/map_tanoabuka.pbo",
    "altis": "Addons/map_altis.pbo",
    "stratis": "Addons/map_stratis.pbo",
    "malden": "Addons/map_malden.pbo",
    "enoch": "Enoch/Addons/map_enoch.pbo",
    "lingor3": os.path.join(WORKSHOP, "718649903", "addons", "lingor3.pbo"),  # mod Lingor/Dingor Island (ruta absoluta)
}
# Mundos cuyo roads.shp no trae todos los caminos (Lingor: 172 tramos, la red del .wrp tiene 17 429): basemap dibuja la red
# de caminos del .wrp (tools/vio_port.py read_wrp), con el tipo por el nombre del modelo.
WRP_ROADS = {"lingor3"}


# =====================================================================================================================
# 1) Formato "rapificado" (lectura: adaptado de work/vio_loadouts/tools/cfgdb.py; escritura: para el perfil sintetico)
# =====================================================================================================================
class RapClass:
    __slots__ = ("name", "vals", "classes")

    def __init__(self, name):
        self.name = name
        self.vals = {}       # nombre en minusculas -> valor
        self.classes = []    # [(nombre, RapClass)] en orden

    def cls(self, name):
        n = name.lower()
        for k, c in self.classes:
            if k.lower() == n:
                return c
        return None


class RapReader:
    def __init__(self, b):
        if b[:4] != b"\0raP":
            raise ValueError("no es un archivo rapificado (no empieza con \\0raP)")
        self.b = b

    def asciiz(self, p):
        e = self.b.index(b"\0", p)
        return self.b[p:e].decode("utf-8", "replace"), e + 1

    def cint(self, p):
        v = sh = 0
        while True:
            c = self.b[p]
            p += 1
            v |= (c & 0x7F) << sh
            sh += 7
            if not c & 0x80:
                return v, p

    def array(self, p):
        n, p = self.cint(p)
        out = []
        b = self.b
        for _ in range(n):
            t = b[p]
            p += 1
            if t in (0, 4):
                s, p = self.asciiz(p)
                out.append(s)
            elif t == 1:
                out.append(struct.unpack_from("<f", b, p)[0])
                p += 4
            elif t == 2:
                out.append(struct.unpack_from("<i", b, p)[0])
                p += 4
            elif t == 3:
                a, p = self.array(p)
                out.append(a)
            elif t == 6:
                out.append(struct.unpack_from("<q", b, p)[0])
                p += 8
            else:
                raise ValueError(f"tipo de elemento de arreglo {t} en {p}")
        return out, p

    def read_class(self, name, off, depth=0):
        if depth > 64:
            raise ValueError("clases demasiado anidadas")
        b = self.b
        c = RapClass(name)
        _inh, p = self.asciiz(off)
        n, p = self.cint(p)
        for _ in range(n):
            t = b[p]
            p += 1
            if t == 0:
                nm, p = self.asciiz(p)
                o = struct.unpack_from("<I", b, p)[0]
                p += 4
                c.classes.append((nm, self.read_class(nm, o, depth + 1)))
            elif t == 1:
                st = b[p]
                p += 1
                nm, p = self.asciiz(p)
                if st in (0, 4):
                    v, p = self.asciiz(p)
                elif st == 1:
                    v = struct.unpack_from("<f", b, p)[0]
                    p += 4
                elif st == 2:
                    v = struct.unpack_from("<i", b, p)[0]
                    p += 4
                elif st == 6:
                    v = struct.unpack_from("<q", b, p)[0]
                    p += 8
                else:
                    v, p = self.asciiz(p)
                c.vals[nm.lower()] = v
            elif t == 2:
                nm, p = self.asciiz(p)
                a, p = self.array(p)
                c.vals[nm.lower()] = a
            elif t in (3, 4):
                _nm, p = self.asciiz(p)
            elif t == 5:
                p += 4
                nm, p = self.asciiz(p)
                a, p = self.array(p)
                c.vals[nm.lower()] = a
            else:
                raise ValueError(f"tipo de entrada {t} en {p}")
        return c

    def root(self):
        return self.read_class("", 16)


def _cint(n):
    out = bytearray()
    while True:
        c = n & 0x7F
        n >>= 7
        if n:
            out.append(c | 0x80)
        else:
            out.append(c)
            return bytes(out)


def _z(s):
    return s.encode("utf-8") + b"\0"


class RapWriter:
    """Escribe un arbol RapClass (vals: str -> str/float/int/list; classes en orden) como archivo rapificado."""

    @staticmethod
    def _val(name, v):
        if isinstance(v, list):
            return b"\x02" + _z(name) + RapWriter._arr(v)
        if isinstance(v, str):
            return b"\x01\x00" + _z(name) + _z(v)
        if isinstance(v, float):
            return b"\x01\x01" + _z(name) + struct.pack("<f", v)
        return b"\x01\x02" + _z(name) + struct.pack("<i", int(v))

    @staticmethod
    def _arr(a):
        out = bytearray(_cint(len(a)))
        for v in a:
            if isinstance(v, list):
                out += b"\x03" + RapWriter._arr(v)
            elif isinstance(v, str):
                out += b"\x00" + _z(v)
            elif isinstance(v, float):
                out += b"\x01" + struct.pack("<f", v)
            else:
                out += b"\x02" + struct.pack("<i", int(v))
        return bytes(out)

    def _body(self, c, offs):
        out = bytearray(b"\0")
        ents = list(c.vals.items())
        out += _cint(len(ents) + len(c.classes))
        for k, v in ents:
            out += self._val(k, v)
        for (nm, _sub), o in zip(c.classes, offs):
            out += b"\x00" + _z(nm) + struct.pack("<I", o)
        return bytes(out)

    def _emit(self, c, pos):
        n = len(c.classes)
        blen = len(self._body(c, [0] * n))
        p = pos + blen
        offs, subs = [], []
        for _nm, sub in c.classes:
            offs.append(p)
            sb = self._emit(sub, p)
            subs.append(sb)
            p += len(sb)
        return self._body(c, offs) + b"".join(subs)

    def write(self, root):
        data = self._emit(root, 16)
        enum_off = 16 + len(data)
        return b"\0raP" + struct.pack("<II", 0, 8) + struct.pack("<I", enum_off) + data + struct.pack("<I", 0)


# ---------------------------------------------------------------- variables del perfil (ProfileVariables)
def pv_value(data):
    """class data de una variable del perfil -> valor de Python (None si el tipo no se usa aqui)."""
    if data is None:
        return None
    t = str(data.vals.get("singletype", "")).upper()
    if t == "SCALAR":
        return float(data.vals.get("value", 0.0))
    if t in ("STRING", "SIDE", "TEXT"):
        return str(data.vals.get("value", ""))
    if t == "BOOL":
        return bool(data.vals.get("value", 0))
    if t == "ARRAY":
        v = data.cls("value")
        if v is None:
            return []
        items = []
        for nm, sub in v.classes:
            m = re.match(r"item(\d+)$", nm, re.I)
            if m:
                items.append((int(m.group(1)), pv_value(sub.cls("data"))))
        items.sort(key=lambda x: x[0])
        return [x[1] for x in items]
    return None


def read_profile(path):
    """{nombre en minusculas: valor} de un .vars.Arma3Profile (solo lectura)."""
    with open(path, "rb") as f:
        b = f.read()
    root = RapReader(b).root()
    pv = root.cls("ProfileVariables")
    out = {}
    if pv is None:
        return out
    for _nm, item in pv.classes:
        name = item.vals.get("name")
        if isinstance(name, str):
            out[name.lower()] = pv_value(item.cls("data"))
    return out


def pv_data(v):
    d = RapClass("data")
    if isinstance(v, bool):
        d.vals["singleType"] = "BOOL"
        d.vals["value"] = int(v)
    elif isinstance(v, (int, float)):
        d.vals["singleType"] = "SCALAR"
        d.vals["value"] = float(v)
    elif isinstance(v, str):
        d.vals["singleType"] = "STRING"
        d.vals["value"] = v
    elif isinstance(v, (list, tuple)):
        d.vals["singleType"] = "ARRAY"
        if len(v):
            val = RapClass("value")
            val.vals["items"] = len(v)
            for i, x in enumerate(v):
                it = RapClass(f"Item{i}")
                it.classes.append(("data", pv_data(x)))
                val.classes.append((f"Item{i}", it))
            d.classes.append(("value", val))
    else:
        d.vals["singleType"] = "NOTHING"
        d.vals["nil"] = 1
    return d


def write_profile(path, variables):
    """Perfil sintetico con la misma estructura que el del juego (nombres en minusculas, como los guarda el juego)."""
    root = RapClass("")
    root.vals["version"] = 2
    pv = RapClass("ProfileVariables")
    pv.vals["items"] = len(variables)
    pv.vals["slots"] = max(1, len(variables))
    for i, (name, v) in enumerate(variables.items()):
        it = RapClass(f"Item{i}")
        it.vals["name"] = name.lower()
        it.classes.append(("data", pv_data(v)))
        it.vals["readOnly"] = 0
        pv.classes.append((f"Item{i}", it))
    root.classes.append(("ProfileVariables", pv))
    data = RapWriter().write(root)
    if os.path.exists(path) and (os.path.abspath(path) == os.path.abspath(DEFAULT_PROFILE)
                                 or os.path.abspath(path).startswith(os.path.dirname(os.path.abspath(GAMEDOCS)) + os.sep)):
        raise SystemExit("no se escribe sobre el perfil real")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


# ---------------------------------------------------------------- texto SQF (copyToClipboard str VIOC_WR_DATA)
def parse_sqf(text):
    """Arreglo SQF en texto (str de un arreglo) -> lista de Python."""
    s = text.strip()
    pos = 0

    def ws():
        nonlocal pos
        while pos < len(s) and s[pos] in " \t\r\n":
            pos += 1

    def val():
        nonlocal pos
        ws()
        c = s[pos]
        if c == "[":
            pos += 1
            out = []
            ws()
            if s[pos] == "]":
                pos += 1
                return out
            while True:
                out.append(val())
                ws()
                if s[pos] == ",":
                    pos += 1
                elif s[pos] == "]":
                    pos += 1
                    return out
                else:
                    raise ValueError(f"se esperaba , o ] en {pos}")
        if c in "\"'":
            q = c
            pos += 1
            buf = []
            while True:
                k = s.index(q, pos)
                buf.append(s[pos:k])
                if k + 1 < len(s) and s[k + 1] == q:
                    buf.append(q)
                    pos = k + 2
                else:
                    pos = k + 1
                    return "".join(buf)
        m = re.compile(r"-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?").match(s, pos)
        if m:
            pos = m.end()
            return float(m.group(0))
        m = re.compile(r"[A-Za-z_<>][\w<>]*").match(s, pos)
        if m:
            pos = m.end()
            w = m.group(0).lower()
            return {"true": True, "false": False}.get(w, None if w in ("any", "<null>", "nil") else m.group(0))
        raise ValueError(f"caracter inesperado {c!r} en {pos}")

    return val()


# =====================================================================================================================
# 2) Registros de la guerra
# =====================================================================================================================
def _num(v, d=0.0):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else d


def _date_str(st):
    if isinstance(st, list) and len(st) >= 5 and all(isinstance(x, (int, float)) for x in st[:5]):
        y, mo, d, h, mi = (int(round(x)) for x in st[:5])
        return f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}"
    return ""


def decode_record(arr, key):
    """Registro VIOCWR1 (lista) -> dict listo para exportar, o None si no es valido."""
    if not (isinstance(arr, list) and len(arr) >= 7 and arr[0] == TAG):
        return None
    meta, towns_raw, ch, ev, sn, st = arr[1], arr[2], arr[3], arr[4], arr[5], arr[6]
    if not (isinstance(meta, list) and isinstance(towns_raw, list) and all(isinstance(x, str) for x in (ch, ev, sn))):
        return None
    meta = meta + [None] * (9 - len(meta))
    unit = _num(meta[8], 10.0) or 10.0
    names = meta[6] if isinstance(meta[6], list) and len(meta[6]) >= 3 else SIDE_DEFAULT_NAMES
    towns = []
    for t in towns_raw:
        if isinstance(t, list) and len(t) >= 4:
            towns.append([str(t[0]), round(_num(t[1])), round(_num(t[2])), int(_num(t[3], -1)), int(_num(t[4] if len(t) > 4 else 0))])
    changes = []
    for e in ch.split(";"):
        f = e.split(",")
        if len(f) == 3:
            try:
                changes.append([int(float(f[0])), int(float(f[1])), int(float(f[2]))])
            except ValueError:
                pass
    events = []
    for e in ev.split(";"):
        f = e.split(",")
        if len(f) >= 6:
            try:
                events.append([int(float(f[0])), f[1], int(float(f[2])), round(float(f[3]) * unit), round(float(f[4]) * unit), int(float(f[5]))])
            except ValueError:
                pass
    snaps = []
    for e in sn.split(";"):
        f = e.split(",")
        if len(f) >= 4:
            try:
                sides = []
                for txt in f[2:4]:
                    pts = []
                    if txt != "-":
                        v = [float(x) for x in txt.split()]
                        pts = [[round(v[i] * unit), round(v[i + 1] * unit)] for i in range(0, len(v) - 1, 2)]
                    sides.append(pts)
                snaps.append([int(float(f[0])), int(float(f[1])), sides[0], sides[1]])
            except ValueError:
                pass
    changes.sort(key=lambda x: x[0])
    events.sort(key=lambda x: x[0])
    snaps.sort(key=lambda x: x[0])
    st = st if isinstance(st, list) else []
    st = st + [None] * (10 - len(st))
    span = int(_num(st[0]))
    for lst in (changes, events, snaps):
        if lst:
            span = max(span, lst[-1][0])
    finished = int(_num(st[1])) == 1
    winner = int(_num(st[2], -1))
    return {
        "key": key, "mission": str(meta[0] or ""), "world": str(meta[1] or ""), "worldSize": _num(meta[2], 0.0),
        "title": str(meta[3] or meta[0] or ""), "start": _date_str(meta[4]), "date0": meta[5] if isinstance(meta[5], list) else [],
        "end": _date_str(st[3]), "sides": [str(x) for x in names[:3]], "version": str(meta[7] or ""), "unit": unit,
        "towns": towns, "changes": changes, "events": events, "snaps": snaps, "span": span,
        "finished": finished, "winner": winner, "trunc": int(_num(st[8])), "snapInt": int(_num(st[9], 120)),
    }


def load_games(args):
    if getattr(args, "sqf", None):
        with open(args.sqf, encoding="utf-8", errors="replace") as f:
            arr = parse_sqf(f.read())
        g = decode_record(arr, os.path.basename(args.sqf))
        return [g] if g else []
    path = args.profile or DEFAULT_PROFILE
    if not os.path.exists(path):
        raise SystemExit(f"no existe el perfil {path}")
    variables = read_profile(path)
    games = []
    for name in sorted(variables):
        if not name.startswith(KEY_PREFIX):
            continue
        val = variables[name]
        if name.endswith("_hist"):
            for i, rec in enumerate(val if isinstance(val, list) else []):
                g = decode_record(rec, f"{name}[{i}]")
                if g:
                    games.append(g)
        else:
            g = decode_record(val, name)
            if g:
                games.append(g)
    games.sort(key=lambda g: (g["start"], g["key"]))
    return games


def side_name(g, s):
    return g["sides"][s] if s in (0, 1, 2) else "sin dueño"


def counts_timeline(g):
    """[[t, oeste, este, resistencia, otros], ...] despues de cada cambio (con el inicio y el final)."""
    own = [t[3] for t in g["towns"]]
    cnt = [0, 0, 0, 0]
    for s in own:
        cnt[s if s in (0, 1, 2) else 3] += 1
    out = [[0] + cnt[:]]
    n = len(own)
    for t, i, s in g["changes"]:
        if 0 <= i < n:
            o = own[i]
            cnt[o if o in (0, 1, 2) else 3] -= 1
            own[i] = s
            cnt[s if s in (0, 1, 2) else 3] += 1
            if out[-1][0] == t:
                out[-1] = [t] + cnt[:]
            else:
                out.append([t] + cnt[:])
    if out[-1][0] < g["span"]:
        out.append([g["span"]] + cnt[:])
    return out


def clock_points(g):
    """[[t, minutos acumulados desde la medianoche del primer dia], ...] (inicio + fotos; vueltas de medianoche)."""
    out = []
    prev = -1
    acc = 0
    d0 = g["date0"]
    if isinstance(d0, list) and len(d0) >= 5:
        prev = int(_num(d0[3])) * 60 + int(_num(d0[4]))
        out.append([0, prev])
    for s in g["snaps"]:
        dm = s[1]
        if prev >= 0 and dm < prev - 30:
            acc += 1440
        prev = dm
        out.append([s[0], dm + acc])
    return out


def hms(s):
    s = max(0, int(round(s)))
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def event_text(g, e):
    t, k, s, x, y, i = e
    sn = side_name(g, s)
    towns = g["towns"]

    def near():
        if not towns:
            return "?"
        return min(towns, key=lambda tw: (tw[1] - x) ** 2 + (tw[2] - y) ** 2)[0]

    tn = towns[i][0] if 0 <= i < len(towns) else near()
    return {
        "cap": f"{sn} toma la CAPITAL, {tn}",
        "af": f"{sn} toma un aeródromo: {tn}",
        "hq": f"Destruido el cuartel general (HQ) de {sn}",
        "base": f"{sn} pierde {i} edificio{'s' if i != 1 else ''} de su base",
        "so": f"Operación especial de {sn} hacia {tn}",
        "cas": f"Ataque A-10 de {sn} cerca de {near()}",
        "gs": f"Cañonero Ghostrider de {sn} sobre {near()}",
        "start": "Empieza la guerra",
        "resume": "Partida reanudada desde el guardado",
        "end": (f"FIN DE LA GUERRA: gana {sn}" if s in (0, 1, 2) else "FIN DE LA PARTIDA"),
    }.get(k, k)


def cmd_list(args):
    games = load_games(args)
    src = args.sqf or args.profile or DEFAULT_PROFILE
    if not games:
        print(f"No hay partidas grabadas en {src}.")
        print("(El parche war_replay graba en el perfil del ANFITRION; la primera aparece al minuto de partida, "
              "en el perfil a los 2 min y en el archivo con el siguiente guardado o al terminar.)")
        return 0
    print(f"{len(games)} partida(s) en {src}:")
    print(f"{'N':>2}  {'empieza':16}  {'dura':>8}  {'estado':10}  {'ganador':12}  {'pueblos':>7}  {'cambios':>7}  {'avisos':>6}  {'fotos':>5}  mision / clave")
    for n, g in enumerate(games, 1):
        estado = "terminada" if g["finished"] else "en curso" if not g["key"].endswith("]") else "cortada"
        win = side_name(g, g["winner"]) if g["finished"] and g["winner"] in (0, 1, 2) else "-"
        print(f"{n:>2}  {g['start'] or '?':16}  {hms(g['span']):>8}  {estado:10}  {win:12}  {len(g['towns']):>7}  "
              f"{len(g['changes']):>7}  {len(g['events']):>6}  {len(g['snaps']):>5}  {g['title']} ({g['world']}) / {g['key']}")
    return 0


def pick_game(games, n):
    if not games:
        raise SystemExit("no hay partidas grabadas (war_replay.py list)")
    if n is None:
        fin = [g for g in games if g["finished"]]
        return (fin or games)[-1]
    if not 1 <= n <= len(games):
        raise SystemExit(f"--game {n}: hay {len(games)} partida(s)")
    return games[n - 1]


# =====================================================================================================================
# 3) Mapas (basemap: pintar y guardar; luego export los usa sin numpy)
# =====================================================================================================================
def maps_dir(args):
    return getattr(args, "maps", None) or MAPS_DIR


def map_files(args, world):
    d = maps_dir(args)
    w = world.lower()
    return os.path.join(d, f"{w}.png"), os.path.join(d, f"{w}_land.png"), os.path.join(d, f"{w}.json")


def _tools_dir():
    cands = [os.environ.get("WAR_REPLAY_TOOLS"), HERE, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "tools")]
    for c in cands:
        if c and os.path.exists(os.path.join(c, "vio_wrp.py")):
            return c
    raise SystemExit("basemap: no encuentro tools/vio_wrp.py (usa WAR_REPLAY_TOOLS=<carpeta tools>)")


def _asciiz(b, p):
    e = b.index(b"\0", p)
    return b[p:e].decode("latin-1"), e + 1


# Tamanio de cada tipo de registro del "map info" de un .wrp OPRW v25 (deducido y comprobado: Tanoa se lee entero).
MI_LAYOUT = {"T1": ("<Iff", 12), "T2": ("<I8f", 36), "T3": ("<II4f", 24), "T4": ("<I8fI", 40), "T5": ("<I4f", 20), "T35": ("<I6fB", 29)}
MI_TYPES = {}
for _t in (0, 1, 2, 10, 11, 13, 14, 15, 16, 17, 22, 23, 26, 27, 30):
    MI_TYPES[_t] = "T1"
for _t in (24, 31, 32, 40):
    MI_TYPES[_t] = "T2"
for _t in (25, 33, 41, 42, 43):
    MI_TYPES[_t] = "T3"
for _t in (3, 4, 8, 9, 18, 19, 20, 21, 28, 29, 36, 37, 38, 39):
    MI_TYPES[_t] = "T4"
MI_TYPES[34] = "T5"
MI_TYPES[35] = "T35"


def read_terrain(pbo):
    """(tamanio del mapa, alturas numpy [fila 0 = sur], {tipo: [registros]} del map info) del .wrp del PBO."""
    import numpy as np
    sys.path.insert(0, _tools_dir())
    import vio_wrp as W  # noqa: E402
    name, b = W.read_entry(pbo, ".wrp")
    if b is None or b[:4] != b"OPRW":
        raise SystemExit(f"{pbo}: no trae un .wrp OPRW")
    ver = struct.unpack_from("<I", b, 4)[0]
    p = 12 if ver >= 25 else 8
    lx, _ly, tx, ty = struct.unpack_from("<4I", b, p)
    p += 16
    cell = struct.unpack_from("<f", b, p)[0]
    p += 4
    p = W._skip_quadtree(b, p)
    p = W._skip_quadtree(b, p)
    npk = struct.unpack_from("<I", b, p)[0]
    p += 4 + 12 * npk
    p = W._skip_quadtree(b, p)
    _, p = W._compressed(b, p, tx * ty)
    _, p = W._compressed(b, p, tx * ty)
    raw, p = W._compressed(b, p, tx * ty * 4)
    elev = np.frombuffer(raw, "<f4").reshape(ty, tx).astype(np.float32)
    mi = {}
    try:
        nmat = struct.unpack_from("<I", b, p)[0]
        p += 4
        for _ in range(nmat):
            _, p = _asciiz(b, p)
            p += 1
        nmod = struct.unpack_from("<I", b, p)[0]
        p += 4
        for _ in range(nmod):
            _, p = _asciiz(b, p)
        ncls = struct.unpack_from("<I", b, p)[0]
        p += 4
        for _ in range(ncls):
            _, p = _asciiz(b, p)
            _, p = _asciiz(b, p)
            p += 16
        p = W._skip_quadtree(b, p)
        p += 4
        p = W._skip_quadtree(b, p)
        size_mapinfo = struct.unpack_from("<I", b, p)[0]
        data = b[len(b) - size_mapinfo:]
        q = 0
        while q + 4 <= len(data):
            t = struct.unpack_from("<I", data, q)[0]
            k = MI_TYPES.get(t)
            if k is None:
                print(f"  map info: tipo {t} desconocido en {q}; se usa lo leido hasta ahi")
                break
            fmt, sz = MI_LAYOUT[k]
            mi.setdefault(t, []).append(struct.unpack_from(fmt, data, q + 4))
            q += 4 + sz
    except Exception as e:  # noqa: BLE001 - el map info es opcional (casas y vegetacion)
        print(f"  map info no leido ({e}); el mapa sale sin casas ni vegetacion")
    return lx * cell, elev, mi


def read_roads(pbos):
    """[(tipo 'main road'/'road'/'track', [(x, y), ...]), ...] de roads.shp + roads.dbf + RoadsLib.cfg (si existen)."""
    sys.path.insert(0, _tools_dir())
    import vio_wrp as W  # noqa: E402
    for pbo in pbos:
        try:
            _n, shp = W.read_entry(pbo, "roads.shp")
        except Exception:  # noqa: BLE001
            shp = None
        if not shp:
            continue
        _n, dbf = W.read_entry(pbo, "roads.dbf")
        _n, lib = W.read_entry(pbo, "roadslib.cfg")
        kinds = {}
        if lib:
            for m in re.finditer(r"class\s+Road0*(\d+)\s*\{(.*?)\};", lib.decode("latin-1"), re.S | re.I):
                mm = re.search(r'map\s*=\s*"([^"]*)"', m.group(2))
                kinds[int(m.group(1))] = (mm.group(1).lower() if mm else "road")
        ids = []
        if dbf:
            nrec, hlen, rlen = struct.unpack_from("<IHH", dbf, 4)
            fields, p = [], 32
            while dbf[p] != 0x0D:
                fields.append((dbf[p:p + 11].split(b"\0")[0].decode("latin-1").upper(), dbf[p + 16]))
                p += 32
            for i in range(nrec):
                r = dbf[hlen + i * rlen:hlen + (i + 1) * rlen]
                q, rid = 1, 0
                for fn, fl in fields:
                    if fn == "ID":
                        try:
                            rid = int(float(r[q:q + fl].decode("latin-1").strip() or 0))
                        except ValueError:
                            rid = 0
                    q += fl
                ids.append(rid)
        bbox = struct.unpack_from("<4d", shp, 36)
        off = 200000.0 if bbox[0] > 100000 else 0.0
        p, k, out = 100, 0, []
        while p + 8 <= len(shp):
            _rn, clen = struct.unpack_from(">2i", shp, p)
            p += 8
            rec = shp[p:p + clen * 2]
            p += clen * 2
            kind = kinds.get(ids[k] if k < len(ids) else 0, "road")
            k += 1
            if len(rec) < 44 or struct.unpack_from("<i", rec, 0)[0] not in (3, 13, 23):
                continue
            nparts, npts = struct.unpack_from("<2i", rec, 36)
            parts = list(struct.unpack_from("<%di" % nparts, rec, 44)) + [npts]
            pts = struct.unpack_from("<%dd" % (npts * 2), rec, 44 + 4 * nparts)
            xy = [(pts[2 * j] - off, pts[2 * j + 1]) for j in range(npts)]
            for a in range(nparts):
                seg = xy[parts[a]:parts[a + 1]]
                if len(seg) >= 2:
                    out.append((kind, seg))
        return out, os.path.basename(pbo)
    return [], ""


def read_wrp_roads(pbo):
    """[(tipo, [(x, y), ...]), ...] de la red de caminos del .wrp: sil*/asfl* = carretera principal, asf*/bridge* = camino,
    el resto (mud*, path*, racetrack*) = pista; sin pistas de aterrizaje ni caminos invisibles."""
    sys.path.insert(0, _tools_dir())
    import vio_port as VPORT  # noqa: E402
    out = []
    for path, pts in VPORT.read_wrp(pbo)["road_parts"]:
        m = path.lower().rsplit("\\", 1)[-1]
        if m.startswith(("runway", "road_invisible")) or len(pts) < 2:
            continue
        kind = "main road" if m.startswith(("sil", "asfl")) else "road" if m.startswith(("asf", "bridge")) else "track"
        out.append((kind, [(float(x), float(y)) for x, y in pts]))
    return out, os.path.basename(pbo) + " (red de caminos del .wrp)"


def _interp_colors(v, stops):
    import numpy as np
    xs = [s[0] for s in stops]
    out = np.zeros(v.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(v, xs, [int(s[1][1 + 2 * c:3 + 2 * c], 16) for s in stops])
    return out


def _blur(a, r):
    """desenfoque de caja separable (r celdas), solo numpy"""
    import numpy as np
    if r < 1:
        return a
    for ax in (0, 1):
        c = np.cumsum(np.pad(a, [(r + 1, r) if i == ax else (0, 0) for i in range(2)], mode="edge"), axis=ax, dtype=np.float64)
        n = a.shape[ax]
        hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=ax)
        lo = np.take(c, np.arange(0, n), axis=ax)
        a = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return a


def cmd_basemap(args):
    import numpy as np
    from PIL import Image, ImageDraw
    world = args.world
    pbo = args.pbo or os.path.join(ARMA, WORLD_PBO.get(world.lower(), ""))
    if not os.path.isfile(pbo):
        raise SystemExit(f"basemap: no encuentro el PBO del terreno ({pbo}); usa --pbo")
    S = args.size
    print(f"basemap {world}: {pbo}")
    ws, elev, mi = read_terrain(pbo)
    base = os.path.splitext(pbo)[0]
    if world.lower() in WRP_ROADS:
        roads, roads_src = read_wrp_roads(pbo)
    else:
        roads, roads_src = read_roads([pbo] + sorted(glob.glob(base + "_data*.pbo")) + sorted(glob.glob(base + "*.pbo")))
    ty, tx = elev.shape
    #--- alturas a S x S (fila 0 = norte)
    f = tx / S
    if abs(f - round(f)) < 1e-6 and int(round(f)) >= 1 and tx % S == 0:
        k = int(round(f))
        E = elev.reshape(ty // k, k, tx // k, k).mean(axis=(1, 3))
    else:
        ii = (np.arange(S) * tx / S).astype(int)
        E = elev[np.ix_((np.arange(S) * ty / S).astype(int), ii)]
    E = E[::-1].astype(np.float32)
    cell = ws / S
    land = E > 0.0
    #--- sombreado (luz del noroeste)
    gy, gx = np.gradient(E, cell)
    dEdx, dEdn = gx, -gy
    z = 2.2
    nx, ny, nz = -dEdx * z, -dEdn * z, np.ones_like(E)
    nn = np.sqrt(nx * nx + ny * ny + nz * nz)
    alt = math.radians(42)
    lx, ly, lz = -math.cos(alt) / math.sqrt(2), math.cos(alt) / math.sqrt(2), math.sin(alt)
    shade = np.clip((nx * lx + ny * ly + nz * lz) / nn, 0, 1) / math.sin(alt)
    #--- colores: tierra por altura, mar por profundidad
    landc = _interp_colors(E, [(0, "#d9cf9e"), (3, "#c4c98f"), (20, "#a6c07f"), (70, "#8fb06c"), (160, "#859a5f"),
                               (280, "#9b8d66"), (420, "#b9ab90"), (600, "#d8d0c0")])
    seac = _interp_colors(-E, [(0, "#9ad6df"), (4, "#6dbfd2"), (15, "#4a9fc2"), (40, "#2f78a8"), (80, "#215a88"), (150, "#1a4570")])
    #--- vegetacion (arboles y arbustos del map info) -> verde oscuro
    veg = np.zeros((S // 4, S // 4), np.float32)
    for t, w in ((0, 1.0), (1, 0.6), (2, 0.35)):
        pts = mi.get(t)
        if pts:
            a = np.array([(r[1], r[2]) for r in pts], np.float32)
            h, _, _ = np.histogram2d(ws - a[:, 1], a[:, 0], bins=S // 4, range=[[0, ws], [0, ws]])
            veg += h.astype(np.float32) * w
    if veg.max() > 0:
        veg = _blur(veg, 2)
        veg = np.clip(veg / max(1e-6, np.percentile(veg[veg > 0], 90)), 0, 1)
        veg = np.kron(veg, np.ones((4, 4), np.float32))[:S, :S]
        forest = np.array([int("4e7a3c"[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
        landc = landc * (1 - 0.5 * veg[..., None]) + forest * (0.5 * veg[..., None])
    sh = (0.62 + 0.45 * shade)[..., None]
    rgb = np.where(land[..., None], landc * sh, seac * (0.9 + 0.12 * shade[..., None]))
    #--- costa: borde de la tierra
    edge = land & ~(np.roll(land, 1, 0) & np.roll(land, -1, 0) & np.roll(land, 1, 1) & np.roll(land, -1, 1))
    rgb[edge] = rgb[edge] * 0.55 + np.array([40, 60, 70], np.float32) * 0.45
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    #--- capa vectorial al doble (suavizado al reducir): casas y caminos
    S2 = S * 2
    vec = Image.new("RGBA", (S2, S2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(vec)
    k2 = S2 / ws

    def P(x, y):
        return (x * k2, (ws - y) * k2)

    nh = 0
    for t in (3, 4, 8, 9, 18, 19, 28, 29, 39):
        for r in mi.get(t, []):
            poly = [P(r[1], r[2]), P(r[3], r[4]), P(r[7], r[8]), P(r[5], r[6])]
            dr.polygon(poly, fill=(92, 80, 68, 235))
            nh += 1
    styles = {"main road": [(3.0 * S2 / 4096 * 2.4, (110, 80, 30, 255)), (2.0 * S2 / 4096 * 2.4, (245, 200, 92, 255))],
              "road": [(2.4 * S2 / 4096 * 2.4, (95, 88, 70, 230)), (1.5 * S2 / 4096 * 2.4, (250, 244, 225, 255))],
              "track": [(1.4 * S2 / 4096 * 2.4, (150, 128, 90, 200))]}
    order = ["track", "road", "main road"]
    for layer in range(2):
        for kind in order:
            st = styles.get(kind, styles["road"])
            if layer >= len(st):
                continue
            wdt, col = st[layer]
            for kd, seg in roads:
                if (kd if kd in styles else "road") == kind:
                    dr.line([P(x, y) for x, y in seg], fill=col, width=max(1, int(round(wdt))), joint="curve")
    vec = vec.resize((S, S), Image.LANCZOS)
    img = Image.alpha_composite(img.convert("RGBA"), vec)
    #--- cuadricula de 1 km (como el mapa del juego), discreta
    grid = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grid)
    km = 1000.0
    for i in range(1, int(ws // km) + 1):
        a = 46 if i % 5 == 0 else 20
        v = i * km * S / ws
        dg.line([(v, 0), (v, S)], fill=(20, 30, 40, a), width=1)
        dg.line([(0, S - v), (S, S - v)], fill=(20, 30, 40, a), width=1)
    img = Image.alpha_composite(img, grid).convert("RGB")
    os.makedirs(maps_dir(args), exist_ok=True)
    fpng, fland, fjson = map_files(args, world)
    img.save(fpng, optimize=True)
    LN = 512
    lm = Image.fromarray((land * 255).astype(np.uint8)).resize((LN, LN), Image.BILINEAR).point(lambda v: 255 if v >= 128 else 0)
    lm.save(fland, optimize=True)
    meta = {"world": world, "worldSize": ws, "size": S, "pbo": os.path.basename(pbo), "roads": roads_src, "nroads": len(roads),
            "houses": nh, "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "note": "fila 0 = norte; x = 0..worldSize de izquierda a derecha"}
    with open(fjson, "w", encoding="utf-8") as fo:
        json.dump(meta, fo, indent=1)
    print(f"  {fpng} ({os.path.getsize(fpng) // 1024} KB, {S}x{S}, {cell:.1f} m/px), {fland}; "
          f"{len(roads)} tramos de camino ({roads_src}), {nh} casas, vegetacion {'si' if mi.get(0) else 'no'}")
    return 0


def load_map(args, g):
    """(imagen RGB o None, mascara de tierra L o None, tamanio del mundo) del mapa guardado del mundo de la partida."""
    from PIL import Image
    fpng, fland, fjson = map_files(args, g["world"] or "?")
    ws = g["worldSize"] or 0
    img = land = None
    if os.path.exists(fpng):
        img = Image.open(fpng).convert("RGB")
        if os.path.exists(fjson):
            with open(fjson, encoding="utf-8") as f:
                ws = json.load(f).get("worldSize", ws) or ws
    if os.path.exists(fland):
        land = Image.open(fland).convert("L")
    if not ws:
        ws = max([max(t[1], t[2]) for t in g["towns"]] + [1000]) * 1.1
    return img, land, ws


# =====================================================================================================================
# 4) Exportar: HTML
# =====================================================================================================================
def _border_color(img):
    """color medio del borde del mapa (el mar) para el fondo fuera de la imagen"""
    im = img.resize((64, 64))
    px = im.load()
    pts = [px[i, 0] for i in range(64)] + [px[i, 63] for i in range(64)] + [px[0, j] for j in range(64)] + [px[63, j] for j in range(64)]
    return "#%02x%02x%02x" % tuple(sum(p[c] for p in pts) // len(pts) for c in range(3))


def _png_data_uri(img, max_px=1600, colors=256):
    from PIL import Image
    im = img
    if im.width > max_px:
        im = im.resize((max_px, max_px), Image.LANCZOS)
    q = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    buf = io.BytesIO()
    q.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), im.width


def _land_bits(land, n=256):
    from PIL import Image
    if land is None:
        return None, 0
    lm = land.resize((n, n), Image.BILINEAR)
    px = lm.load()
    bits = bytearray((n * n + 7) // 8)
    for j in range(n):
        for i in range(n):
            if px[i, j] >= 128:
                k = j * n + i
                bits[k >> 3] |= 1 << (k & 7)
    return base64.b64encode(bytes(bits)).decode("ascii"), n


def build_payload(g, args, ws, bg_uri, land_b64, land_n, sea=None):
    names = [s.strip() for s in args.names.split(",")] if getattr(args, "names", None) else g["sides"]
    names = (names + SIDE_DEFAULT_NAMES)[:3]
    return {
        "title": g["title"], "mission": g["mission"], "world": g["world"], "worldSize": ws, "start": g["start"], "end": g["end"],
        "finished": g["finished"], "winner": g["winner"], "sides": names, "span": g["span"], "towns": g["towns"],
        "changes": g["changes"], "events": [e + [event_text(dict(g, sides=names), e)] for e in g["events"]],
        "snaps": g["snaps"], "clock": clock_points(g), "counts": counts_timeline(g), "seconds": args.seconds,
        "cellMax": max(1500.0, ws / 32 * 4), "map": {"img": bg_uri, "land": land_b64, "landN": land_n, "sea": sea},
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "key": g["key"],
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Historia de la guerra</title>
<style>
:root {
  color-scheme: light;
  --bg: #f4f3ef; --surface: #fcfcfb; --surface-2: #efede7; --border: #dcd9cf;
  --text: #0b0b0b; --text-2: #52514e; --muted: #77756d; --accent: #a8650f; --accent-ink: #ffffff;
  --west: #3987e5; --east: #e0503a; --res: #199e70; --none: #8d8c86; --sea: #1a4570;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #121211; --surface: #1a1a19; --surface-2: #242422; --border: #353530;
    --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e86; --accent: #f0b35a; --accent-ink: #1a1a19;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #121211; --surface: #1a1a19; --surface-2: #242422; --border: #353530;
  --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e86; --accent: #f0b35a; --accent-ink: #1a1a19;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width: 1440px; margin: 0 auto; padding: 16px; }
header { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 16px; margin-bottom: 12px; }
h1 { font-size: 20px; margin: 0; font-weight: 650; letter-spacing: .01em; }
.sub { color: var(--text-2); font-size: 13px; }
.result { font-weight: 600; }
.grid { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 16px; align-items: start; }
@media (max-width: 960px) { .grid { grid-template-columns: minmax(0, 1fr); } }
.mapbox { position: relative; background: var(--sea); border-radius: 10px; overflow: hidden; aspect-ratio: 1 / 1; max-height: calc(100vh - 150px); width: 100%; margin: 0 auto; touch-action: none; }
#map { width: 100%; height: 100%; display: block; cursor: grab; }
#map.drag { cursor: grabbing; }
.hud { position: absolute; left: 10px; top: 10px; background: rgba(12, 14, 16, .74); color: #f0efec; padding: 6px 10px; border-radius: 8px; font-variant-numeric: tabular-nums; pointer-events: none; font-size: 13px; }
.hud b { font-size: 16px; }
.cap { position: absolute; left: 10px; right: 10px; bottom: 10px; display: flex; flex-direction: column; gap: 4px; align-items: flex-start; pointer-events: none; }
.cap div { background: rgba(12, 14, 16, .74); color: #f0efec; padding: 4px 9px; border-radius: 6px; font-size: 13px; transition: opacity .4s; }
.tip { position: absolute; pointer-events: none; background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 5px 8px; font-size: 12px; box-shadow: 0 2px 10px rgba(0,0,0,.25); display: none; white-space: nowrap; z-index: 3; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 10px; }
button, select { font: inherit; color: var(--text); background: var(--surface); border: 1px solid var(--border); border-radius: 7px; padding: 6px 11px; cursor: pointer; }
button:hover, select:hover { border-color: var(--muted); }
button.primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); font-weight: 600; min-width: 112px; }
button[aria-pressed="false"] { color: var(--muted); }
input[type=range] { flex: 1 1 220px; accent-color: var(--accent); min-width: 120px; }
.time { font-variant-numeric: tabular-nums; color: var(--text-2); min-width: 150px; text-align: right; }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; margin-bottom: 12px; }
.panel h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--text-2); margin: 0 0 8px; font-weight: 600; }
.counts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.chip { min-width: 0; }
.chip .lab { display: flex; align-items: center; gap: 6px; color: var(--text-2); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chip .n { font-size: 24px; font-weight: 650; font-variant-numeric: tabular-nums; }
.sw { width: 10px; height: 10px; border-radius: 2px; flex: none; }
.dom { display: flex; height: 10px; border-radius: 5px; overflow: hidden; gap: 2px; margin-top: 8px; background: var(--surface); }
.dom span { height: 100%; transition: flex-grow .25s; }
#chart { width: 100%; height: 180px; display: block; }
.chartwrap { position: relative; }
.events { max-height: 330px; overflow: auto; margin: 0 -4px; padding: 0 4px; }
.ev { display: grid; grid-template-columns: 62px minmax(0, 1fr); gap: 8px; padding: 5px 0; border-top: 1px solid var(--border); font-size: 13px; color: var(--muted); cursor: pointer; }
.ev:first-child { border-top: 0; }
.ev.past { color: var(--text); }
.ev.major.past { font-weight: 600; }
.ev .t { font-variant-numeric: tabular-nums; color: var(--text-2); }
.legend-note { color: var(--muted); font-size: 12px; margin-top: 6px; }
footer { color: var(--muted); font-size: 12px; margin-top: 4px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1 id="title">Historia de la guerra</h1>
      <div class="sub" id="sub"></div>
    </div>
    <div class="result" id="result"></div>
  </header>
  <div class="grid">
    <section>
      <div class="mapbox" id="mapbox">
        <canvas id="map" aria-label="Mapa de la guerra: pueblos coloreados por bando a lo largo del tiempo" role="img"></canvas>
        <div class="hud" id="hud"></div>
        <div class="cap" id="cap"></div>
        <div class="tip" id="tip"></div>
      </div>
      <div class="controls">
        <button class="primary" id="play" aria-label="Reproducir o pausar">&#9654; Reproducir</button>
        <select id="speed" aria-label="Duración de la repetición">
          <option value="30">30 s</option><option value="60">60 s</option><option value="120">120 s</option><option value="300">5 min</option>
        </select>
        <input type="range" id="scrub" min="0" max="1" step="1" value="0" aria-label="Momento de la guerra">
        <span class="time" id="time"></span>
      </div>
      <div class="controls">
        <button id="tZones" aria-pressed="true">Zonas</button>
        <button id="tTeams" aria-pressed="true">Equipos</button>
        <button id="tNames" aria-pressed="false">Todos los nombres</button>
        <button id="tFit">Encuadrar</button>
        <span class="legend-note">Rueda o pellizco: zoom &middot; arrastrar: mover &middot; espacio: reproducir/pausa &middot; doble clic: encuadrar</span>
      </div>
    </section>
    <aside>
      <div class="panel">
        <h2>Pueblos por bando</h2>
        <div class="counts" id="counts"></div>
        <div class="dom" id="dom" aria-hidden="true"></div>
        <div class="legend-note">&#9670; capital &middot; &#9650; aeródromo &middot; &#9632; equipo (jefe de escuadra, foto cada 2 min)</div>
      </div>
      <div class="panel">
        <h2>Pueblos en el tiempo</h2>
        <div class="chartwrap"><canvas id="chart" aria-label="Grafica de pueblos de cada bando a lo largo de la partida" role="img"></canvas><div class="tip" id="ctip"></div></div>
      </div>
      <div class="panel">
        <h2>Avisos</h2>
        <div class="events" id="events" role="list"></div>
      </div>
    </aside>
  </div>
  <footer id="foot"></footer>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
"use strict";
(function () {
const D = JSON.parse(document.getElementById("data").textContent);
const $ = (id) => document.getElementById(id);
const N = D.towns.length, WS = D.worldSize, SPAN = Math.max(1, D.span);
const SIDEV = ["--west", "--east", "--res", "--none"];
let COL = [];
function readColors() { const cs = getComputedStyle(document.documentElement); COL = SIDEV.map((v) => cs.getPropertyValue(v).trim()); }
readColors();
const si = (s) => (s === 0 || s === 1 || s === 2) ? s : 3;
const NAMES = D.sides.concat(["sin dueño"]);
if (D.map.sea) document.documentElement.style.setProperty("--sea", D.map.sea);
const fmt = (s) => { s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60; return h + ":" + String(m).padStart(2, "0") + ":" + String(x).padStart(2, "0"); };
const fmtShort = (s) => { s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h + ":" + String(m).padStart(2, "0"); };
function esc(t) { return String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

//--- cabecera
$("title").textContent = "Historia de la guerra" + (D.title ? " — " + D.title : "");
$("sub").textContent = [D.world, D.start ? "empezó " + D.start : "", D.end ? "terminó " + D.end : "", "duración " + fmt(SPAN)].filter(Boolean).join(" · ");
$("result").innerHTML = D.finished ? (D.winner >= 0 && D.winner <= 2 ? 'Gana <span style="color:' + COL[D.winner] + '">■</span> ' + esc(NAMES[D.winner]) : "Partida terminada") : "Partida sin terminar";
$("foot").textContent = "Exportado " + D.generated + " con war_replay.py · " + D.key + " · " + N + " pueblos, " + D.changes.length + " cambios de dueño, " + D.events.length + " avisos, " + D.snaps.length + " fotos de equipos.";

//--- estado en el tiempo
const T0 = D.towns.map((t) => t[3]);
let owners = T0.slice(), cPtr = 0, curT = 0, playing = false, dur = D.seconds || 60;
const lastCap = new Float64Array(N).fill(-1e9), capCount = new Int32Array(N);
function applyTo(t) {
  if (t < curT) { owners = T0.slice(); cPtr = 0; lastCap.fill(-1e9); capCount.fill(0); }
  while (cPtr < D.changes.length && D.changes[cPtr][0] <= t) {
    const c = D.changes[cPtr]; if (c[1] >= 0 && c[1] < N) { owners[c[1]] = c[2]; lastCap[c[1]] = c[0]; capCount[c[1]]++; } cPtr++;
  }
  curT = t; terrDirty = true;
}
function idxAt(arr, t) { let lo = 0, hi = arr.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m][0] <= t) { r = m; lo = m + 1; } else hi = m - 1; } return r; }
function clockAt(t) {
  const c = D.clock; if (!c.length) return "";
  let k = Math.max(0, idxAt(c, t)), mm = c[k][1];
  if (k + 1 < c.length && c[k][0] <= t) { const f = Math.min(1, (t - c[k][0]) / Math.max(1, c[k + 1][0] - c[k][0])); mm += (c[k + 1][1] - mm) * Math.max(0, f); }
  const day = Math.floor(mm / 1440) + 1, hm = Math.floor(mm) % 1440;
  return "Día " + day + " · " + String(Math.floor(hm / 60)).padStart(2, "0") + ":" + String(hm % 60).padStart(2, "0");
}

//--- mapa: fondo, mascara de tierra y zonas (pueblo mas cercano en tierra)
const bg = new Image(); let bgOk = false;
if (D.map.img) { bg.onload = () => { bgOk = true; draw(); }; bg.src = D.map.img; }
let land = null; const LN = D.map.landN || 0;
if (D.map.land) { const s = atob(D.map.land); land = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) land[i] = s.charCodeAt(i); }
function isLand(x, y) {
  if (!land) return null;
  const i = Math.floor(x / WS * LN), j = Math.floor((1 - y / WS) * LN);
  if (i < 0 || j < 0 || i >= LN || j >= LN) return false;
  const k = j * LN + i; return (land[k >> 3] >> (k & 7)) & 1;
}
const TN = 320, tIdx = new Int16Array(TN * TN).fill(-1);
(function () {
  const maxD2 = D.cellMax * D.cellMax, fallback2 = 1200 * 1200;
  for (let j = 0; j < TN; j++) for (let i = 0; i < TN; i++) {
    const x = (i + 0.5) / TN * WS, y = (1 - (j + 0.5) / TN) * WS, l = isLand(x, y);
    if (l === 0 || l === false) continue;
    let b = -1, bd = l === null ? fallback2 : maxD2;
    for (let k = 0; k < N; k++) { const dx = D.towns[k][1] - x, dy = D.towns[k][2] - y, d = dx * dx + dy * dy; if (d < bd) { bd = d; b = k; } }
    tIdx[j * TN + i] = b;
  }
})();
const terr = document.createElement("canvas"); terr.width = TN; terr.height = TN;
const tctx = terr.getContext("2d"); const timg = tctx.createImageData(TN, TN);
let terrDirty = true;
function hexRgb(h) { h = h.replace("#", ""); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
function paintTerr() {
  const rgb = COL.map(hexRgb), d = timg.data;
  for (let p = 0; p < TN * TN; p++) {
    const k = tIdx[p], o = p * 4;
    if (k < 0) { d[o + 3] = 0; continue; }
    const c = rgb[si(owners[k])]; d[o] = c[0]; d[o + 1] = c[1]; d[o + 2] = c[2]; d[o + 3] = 255;
  }
  tctx.putImageData(timg, 0, 0); terrDirty = false;
}

//--- vista (zoom y desplazamiento)
const cv = $("map"), ctx = cv.getContext("2d"), box = $("mapbox");
let view = { cx: WS / 2, cy: WS / 2, s: 1 }, dpr = 1;
function fit() {
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  for (const t of D.towns) { x0 = Math.min(x0, t[1]); x1 = Math.max(x1, t[1]); y0 = Math.min(y0, t[2]); y1 = Math.max(y1, t[2]); }
  if (!N) { x0 = y0 = 0; x1 = y1 = WS; }
  const m = Math.max(600, 0.05 * WS); x0 -= m; x1 += m; y0 -= m; y1 += m;
  view.cx = (x0 + x1) / 2; view.cy = (y0 + y1) / 2;
  view.s = Math.min(cv.width / (x1 - x0), cv.height / (y1 - y0));
}
let fitted = false;
function resize() {
  dpr = window.devicePixelRatio || 1;
  const r = box.getBoundingClientRect(), ow = cv.width;
  cv.width = Math.max(10, Math.round(r.width * dpr)); cv.height = Math.max(10, Math.round(r.height * dpr));
  if (!fitted) { fit(); fitted = true; } else if (ow > 0) view.s *= cv.width / ow;
  draw(); drawChart();
}
const W2S = (x, y) => [cv.width / 2 + (x - view.cx) * view.s, cv.height / 2 - (y - view.cy) * view.s];
const S2W = (px, py) => [view.cx + (px - cv.width / 2) / view.s, view.cy - (py - cv.height / 2) / view.s];

let showZones = true, showTeams = true, showNames = false;
function shape(k, x, y, r) {
  const f = D.towns[k][4];
  ctx.beginPath();
  if (f & 1) { ctx.moveTo(x, y - r * 1.5); ctx.lineTo(x + r * 1.5, y); ctx.lineTo(x, y + r * 1.5); ctx.lineTo(x - r * 1.5, y); ctx.closePath(); }
  else if (f & 2) { ctx.moveTo(x, y - r * 1.4); ctx.lineTo(x + r * 1.3, y + r * 0.9); ctx.lineTo(x - r * 1.3, y + r * 0.9); ctx.closePath(); }
  else ctx.arc(x, y, r, 0, Math.PI * 2);
}
function draw() {
  if (terrDirty) paintTerr();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--sea").trim() || "#1a4570";
  ctx.fillRect(0, 0, cv.width, cv.height);
  const [ax, ay] = W2S(0, WS), sz = WS * view.s;
  ctx.imageSmoothingEnabled = true;
  if (bgOk) ctx.drawImage(bg, ax, ay, sz, sz);
  else { ctx.fillStyle = "#d9cf9e"; ctx.globalAlpha = 0.25; ctx.fillRect(ax, ay, sz, sz); ctx.globalAlpha = 1; }
  if (showZones) { ctx.globalAlpha = 0.42; ctx.drawImage(terr, ax, ay, sz, sz); ctx.globalAlpha = 1; }
  ctx.strokeStyle = "rgba(0,0,0,.35)"; ctx.lineWidth = 1.5 * dpr; ctx.strokeRect(ax, ay, sz, sz);
  const ui = dpr * Math.min(1.6, Math.max(0.8, Math.sqrt(view.s * WS / 1200)));
  //--- equipos (foto vigente)
  if (showTeams) {
    const k = idxAt(D.snaps, curT);
    if (k >= 0) {
      const sp = D.snaps[k];
      for (let sd = 0; sd < 2; sd++) {
        ctx.fillStyle = COL[sd]; ctx.strokeStyle = "rgba(10,10,10,.8)"; ctx.lineWidth = 1 * dpr;
        for (const p of sp[2 + sd]) { const [x, y] = W2S(p[0], p[1]); const r = 2.6 * ui; ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.strokeRect(x - r, y - r, 2 * r, 2 * r); }
      }
    }
  }
  //--- destellos de las capturas (1.4 s reales)
  const win = 1.4 * SPAN / dur;
  for (let i = 0; i < N; i++) {
    const age = curT - lastCap[i];
    if (age >= 0 && age < win) {
      const f = age / win, [x, y] = W2S(D.towns[i][1], D.towns[i][2]);
      ctx.beginPath(); ctx.arc(x, y, (8 + 34 * f) * ui, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,255,255," + (1 - f).toFixed(3) + ")"; ctx.lineWidth = 2.5 * dpr; ctx.stroke();
    }
  }
  for (const e of D.events) {
    if (e[0] > curT) break;
    const age = curT - e[0];
    if (age < win * 1.5 && (e[3] || e[4]) && ["start", "resume", "end"].indexOf(e[1]) < 0) {
      const f = age / (win * 1.5), [x, y] = W2S(e[3], e[4]);
      ctx.beginPath(); ctx.arc(x, y, (10 + 50 * f) * ui, 0, Math.PI * 2);
      ctx.strokeStyle = (e[1] === "cap" || e[1] === "af" ? "rgba(255,214,90," : "rgba(255,140,40,") + (1 - f).toFixed(3) + ")"; ctx.lineWidth = 3 * dpr; ctx.stroke();
    }
  }
  //--- pueblos
  for (let i = 0; i < N; i++) {
    const t = D.towns[i], [x, y] = W2S(t[1], t[2]), r = (t[4] ? 5.2 : 4.2) * ui;
    shape(i, x, y, r); ctx.fillStyle = COL[si(owners[i])]; ctx.fill();
    ctx.lineWidth = 1.6 * dpr; ctx.strokeStyle = "rgba(255,255,255,.95)"; ctx.stroke();
  }
  //--- nombres (capital y aerodromos siempre; el resto con "Todos los nombres")
  ctx.font = (600) + " " + Math.round(11.5 * ui) + "px system-ui, -apple-system, Segoe UI, sans-serif";
  ctx.textBaseline = "middle"; ctx.lineJoin = "round";
  for (let i = 0; i < N; i++) {
    const t = D.towns[i]; if (!t[4] && !showNames) continue;
    const [x, y] = W2S(t[1], t[2]), r = (t[4] ? 5.2 : 4.2) * ui;
    ctx.lineWidth = 3 * dpr; ctx.strokeStyle = "rgba(10,12,14,.75)"; ctx.strokeText(t[0], x + r + 4 * dpr, y);
    ctx.fillStyle = "#ffffff"; ctx.fillText(t[0], x + r + 4 * dpr, y);
  }
  updateText();
}

//--- textos: reloj, pueblos por bando, avisos
const countsEl = $("counts"), domEl = $("dom");
countsEl.innerHTML = [0, 1, 2, 3].map((s) => '<div class="chip"><div class="lab"><span class="sw" style="background:var(' + SIDEV[s] + ')"></span>' + esc(NAMES[s]) + '</div><div class="n" id="n' + s + '">0</div></div>').join("");
domEl.innerHTML = [0, 1, 2, 3].map((s) => '<span id="d' + s + '" style="background:var(' + SIDEV[s] + ')"></span>').join("");
const evEl = $("events"), MAJOR = ["cap", "af", "hq", "end", "start"];
evEl.innerHTML = D.events.map((e, k) => '<div class="ev' + (MAJOR.indexOf(e[1]) >= 0 ? " major" : "") + '" role="listitem" data-k="' + k + '"><span class="t">' + fmt(e[0]) + '</span><span>' + esc(e[6]) + '</span></div>').join("") || '<div class="ev">Sin avisos</div>';
evEl.addEventListener("click", (ev) => { const r = ev.target.closest(".ev"); if (r && r.dataset.k) { seek(D.events[+r.dataset.k][0]); } });
let lastPast = -2;
function updateText() {
  const cnt = [0, 0, 0, 0]; for (const s of owners) cnt[si(s)]++;
  for (let s = 0; s < 4; s++) { $("n" + s).textContent = cnt[s]; $("d" + s).style.flexGrow = cnt[s]; }
  $("hud").innerHTML = "<b>" + esc(clockAt(curT) || fmt(curT)) + "</b><br>partida " + fmt(curT) + " / " + fmt(SPAN);
  $("time").textContent = fmt(curT) + " / " + fmt(SPAN);
  $("scrub").value = Math.round(curT);
  const past = idxAt(D.events, curT);
  if (past !== lastPast) {
    evEl.querySelectorAll(".ev").forEach((r, k) => r.classList.toggle("past", k <= past));
    if (playing && past >= 0) { const r = evEl.querySelector('[data-k="' + past + '"]'); if (r) r.scrollIntoView({ block: "nearest" }); }
    lastPast = past;
  }
  //--- avisos recientes sobre el mapa (8 s reales)
  const win = 8 * SPAN / dur, caps = [];
  for (let k = past; k >= 0 && caps.length < 3; k--) { const e = D.events[k]; if (curT - e[0] > win) break; caps.push('<div style="opacity:' + Math.max(0.25, 1 - (curT - e[0]) / win).toFixed(2) + '">' + esc(fmt(e[0]) + "  " + e[6]) + "</div>"); }
  $("cap").innerHTML = caps.join("");
  drawChart();
}

//--- grafica: pueblos de cada bando en el tiempo (escalones), cursor del momento y tooltip
const ch = $("chart"), cctx = ch.getContext("2d"), ctip = $("ctip");
let hoverT = null;
function drawChart() {
  const r = ch.getBoundingClientRect(), pr = window.devicePixelRatio || 1;
  if (ch.width !== Math.round(r.width * pr)) { ch.width = Math.round(r.width * pr); ch.height = Math.round(r.height * pr); }
  const W = ch.width, H = ch.height, L = 30 * pr, R = 80 * pr, T = 8 * pr, B = 20 * pr;
  const cs = getComputedStyle(document.documentElement), ink2 = cs.getPropertyValue("--text-2").trim(), grid = cs.getPropertyValue("--border").trim(), surf = cs.getPropertyValue("--surface").trim();
  cctx.setTransform(1, 0, 0, 1, 0, 0); cctx.clearRect(0, 0, W, H);
  const X = (t) => L + (W - L - R) * t / SPAN, Y = (v) => H - B - (H - B - T) * v / Math.max(1, N);
  cctx.font = Math.round(10.5 * pr) + "px system-ui, sans-serif"; cctx.fillStyle = ink2; cctx.strokeStyle = grid; cctx.lineWidth = 1;
  const step = N > 40 ? 20 : N > 16 ? 10 : 5;
  cctx.textAlign = "right"; cctx.textBaseline = "middle";
  for (let v = 0; v <= N; v += step) { cctx.beginPath(); cctx.moveTo(L, Y(v)); cctx.lineTo(W - R, Y(v)); cctx.stroke(); cctx.fillText(v, L - 5 * pr, Y(v)); }
  cctx.textAlign = "center"; cctx.textBaseline = "top";
  const tick = SPAN > 4 * 3600 ? 3600 : SPAN > 5400 ? 1800 : SPAN > 1800 ? 600 : 300;
  for (let t = 0; t <= SPAN; t += tick) cctx.fillText(fmtShort(t), X(t), H - B + 5 * pr);
  const C = D.counts;
  for (const s of [3, 2, 1, 0]) {
    cctx.beginPath(); cctx.lineWidth = 2 * pr; cctx.strokeStyle = COL[s]; cctx.setLineDash(s === 3 ? [4 * pr, 3 * pr] : []);
    for (let k = 0; k < C.length; k++) { const x = X(C[k][0]), y = Y(C[k][1 + s]); if (k === 0) cctx.moveTo(x, y); else { cctx.lineTo(x, Y(C[k - 1][1 + s])); cctx.lineTo(x, y); } }
    cctx.stroke(); cctx.setLineDash([]);
  }
  //--- etiquetas directas al final de cada linea (sin solaparse)
  const ends = [0, 1, 2, 3].map((s) => ({ s, y: Y(C[C.length - 1][1 + s]) })).sort((a, b) => a.y - b.y);
  for (let k = 1; k < ends.length; k++) if (ends[k].y - ends[k - 1].y < 12 * pr) ends[k].y = ends[k - 1].y + 12 * pr;
  if (ends.length && ends[ends.length - 1].y > H - B) { ends[ends.length - 1].y = H - B; for (let k = ends.length - 2; k >= 0; k--) if (ends[k + 1].y - ends[k].y < 12 * pr) ends[k].y = ends[k + 1].y - 12 * pr; }
  cctx.textAlign = "left"; cctx.textBaseline = "middle";
  for (const e of ends) { cctx.fillStyle = COL[e.s]; cctx.fillRect(W - R + 6 * pr, e.y - 3 * pr, 6 * pr, 6 * pr); cctx.fillStyle = ink2; const nm = NAMES[e.s]; cctx.fillText(nm.length > 11 ? nm.slice(0, 10) + "…" : nm, W - R + 15 * pr, e.y); }
  //--- momento actual
  cctx.strokeStyle = cs.getPropertyValue("--accent").trim(); cctx.lineWidth = 1.5 * pr;
  cctx.beginPath(); cctx.moveTo(X(curT), T); cctx.lineTo(X(curT), H - B); cctx.stroke();
  if (hoverT !== null) {
    const k = Math.max(0, idxAt(C, hoverT)), hx = X(hoverT);
    cctx.strokeStyle = ink2; cctx.lineWidth = 1 * pr; cctx.setLineDash([3 * pr, 3 * pr]); cctx.beginPath(); cctx.moveTo(hx, T); cctx.lineTo(hx, H - B); cctx.stroke(); cctx.setLineDash([]);
    for (let s = 0; s < 4; s++) { cctx.beginPath(); cctx.arc(hx, Y(C[k][1 + s]), 4 * pr, 0, Math.PI * 2); cctx.fillStyle = COL[s]; cctx.fill(); cctx.lineWidth = 2 * pr; cctx.strokeStyle = surf; cctx.stroke(); }
    ctip.style.display = "block";
    ctip.innerHTML = "<b>" + fmt(hoverT) + "</b><br>" + [0, 1, 2, 3].map((s) => '<span class="sw" style="display:inline-block;background:var(' + SIDEV[s] + ')"></span> ' + esc(NAMES[s]) + ": " + C[k][1 + s]).join("<br>");
    const cx = hx / pr; ctip.style.left = Math.min(r.width - 150, cx + 12) + "px"; ctip.style.top = "4px";
  } else ctip.style.display = "none";
}
ch.addEventListener("mousemove", (e) => { const r = ch.getBoundingClientRect(), pr = window.devicePixelRatio || 1, L = 30, R = 80; const t = (e.clientX - r.left - L) / (r.width - L - R) * SPAN; hoverT = (t >= 0 && t <= SPAN) ? t : null; drawChart(); });
ch.addEventListener("mouseleave", () => { hoverT = null; drawChart(); });
ch.addEventListener("click", (e) => { const r = ch.getBoundingClientRect(), L = 30, R = 80; const t = (e.clientX - r.left - L) / (r.width - L - R) * SPAN; if (t >= 0 && t <= SPAN) seek(t); });

//--- controles
const playBtn = $("play"), scrub = $("scrub"), speed = $("speed");
scrub.max = Math.round(SPAN); speed.value = String([30, 60, 120, 300].indexOf(dur) >= 0 ? dur : 60); dur = +speed.value;
function setPlay(p) { playing = p; playBtn.innerHTML = p ? "&#10074;&#10074; Pausa" : "&#9654; Reproducir"; if (p) { if (curT >= SPAN) applyTo(0); last = performance.now(); requestAnimationFrame(tick); } }
function seek(t) { applyTo(Math.max(0, Math.min(SPAN, t))); draw(); }
playBtn.addEventListener("click", () => setPlay(!playing));
scrub.addEventListener("input", () => seek(+scrub.value));
speed.addEventListener("change", () => { dur = +speed.value; });
function toggle(btn, get, set) { btn.addEventListener("click", () => { set(!get()); btn.setAttribute("aria-pressed", String(get())); draw(); }); }
toggle($("tZones"), () => showZones, (v) => { showZones = v; });
toggle($("tTeams"), () => showTeams, (v) => { showTeams = v; });
toggle($("tNames"), () => showNames, (v) => { showNames = v; });
$("tFit").addEventListener("click", () => { fit(); draw(); });
document.addEventListener("keydown", (e) => { if (e.code === "Space" && e.target.tagName !== "SELECT" && e.target.tagName !== "BUTTON") { e.preventDefault(); setPlay(!playing); } if (e.code === "ArrowRight") seek(curT + SPAN / 100); if (e.code === "ArrowLeft") seek(curT - SPAN / 100); });
let last = 0;
function tick(now) {
  if (!playing) return;
  const dt = Math.min(0.25, (now - last) / 1000); last = now;
  applyTo(Math.min(SPAN, curT + dt * SPAN / dur)); draw();
  if (curT >= SPAN) { setPlay(false); return; }
  requestAnimationFrame(tick);
}

//--- zoom y arrastre (raton y tactil) + tooltip de pueblos
const tip = $("tip"); let drag = null; const pts = new Map();
function zoomAt(px, py, f) { const [wx, wy] = S2W(px, py); view.s = Math.max(cv.width / (WS * 3), Math.min(cv.width / 300, view.s * f)); const [nx, ny] = S2W(px, py); view.cx += wx - nx; view.cy += wy - ny; draw(); }
cv.addEventListener("wheel", (e) => { e.preventDefault(); const r = cv.getBoundingClientRect(); zoomAt((e.clientX - r.left) * dpr, (e.clientY - r.top) * dpr, Math.exp(-e.deltaY * 0.0015)); }, { passive: false });
cv.addEventListener("pointerdown", (e) => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); drag = { x: e.clientX, y: e.clientY, d: 0 }; cv.classList.add("drag"); });
cv.addEventListener("pointerup", (e) => { pts.delete(e.pointerId); if (!pts.size) { drag = null; cv.classList.remove("drag"); } });
cv.addEventListener("pointercancel", (e) => { pts.delete(e.pointerId); drag = null; cv.classList.remove("drag"); });
cv.addEventListener("pointermove", (e) => {
  const r = cv.getBoundingClientRect();
  if (pts.has(e.pointerId) && pts.size === 2) {
    const [a, b] = [...pts.values()], d0 = Math.hypot(a[0] - b[0], a[1] - b[1]);
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    const [c, d] = [...pts.values()], d1 = Math.hypot(c[0] - d[0], c[1] - d[1]);
    if (d0 > 0) zoomAt(((c[0] + d[0]) / 2 - r.left) * dpr, ((c[1] + d[1]) / 2 - r.top) * dpr, d1 / d0);
    return;
  }
  if (drag) { pts.set(e.pointerId, [e.clientX, e.clientY]); view.cx -= (e.clientX - drag.x) * dpr / view.s; view.cy += (e.clientY - drag.y) * dpr / view.s; drag.x = e.clientX; drag.y = e.clientY; tip.style.display = "none"; draw(); return; }
  const px = (e.clientX - r.left) * dpr, py = (e.clientY - r.top) * dpr; let best = -1, bd = (14 * dpr) ** 2;
  for (let i = 0; i < N; i++) { const [x, y] = W2S(D.towns[i][1], D.towns[i][2]); const dd = (x - px) ** 2 + (y - py) ** 2; if (dd < bd) { bd = dd; best = i; } }
  if (best >= 0) {
    const t = D.towns[best], s = si(owners[best]);
    tip.innerHTML = "<b>" + esc(t[0]) + "</b>" + (t[4] & 1 ? " (capital)" : t[4] & 2 ? " (aeródromo)" : "") + '<br><span class="sw" style="display:inline-block;background:var(' + SIDEV[s] + ')"></span> ' + esc(NAMES[s]) + " · cambió de dueño " + capCount[best] + (capCount[best] === 1 ? " vez" : " veces") + " hasta ahora";
    tip.style.display = "block"; tip.style.left = Math.min(r.width - 230, e.clientX - r.left + 14) + "px"; tip.style.top = (e.clientY - r.top + 14) + "px";
  } else tip.style.display = "none";
});
cv.addEventListener("pointerleave", () => { tip.style.display = "none"; });
cv.addEventListener("dblclick", () => { fit(); draw(); });
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { readColors(); terrDirty = true; draw(); });
window.addEventListener("resize", resize);
resize();
applyTo(0); draw();
const hm = /t=(\d+(?:\.\d+)?)/.exec(location.hash); if (hm) seek(+hm[1]);
if (/play/.test(location.hash)) setPlay(true);
})();
</script>
</body>
</html>
"""


def export_html(g, args, out):
    img, land, ws = load_map(args, g)
    bg_uri, bg_px = _png_data_uri(img) if img is not None else (None, 0)
    land_b64, land_n = _land_bits(land, 256)
    payload = build_payload(g, args, ws, bg_uri, land_b64, land_n, _border_color(img) if img is not None else None)
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DATA__", js)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML: {out} ({os.path.getsize(out) // 1024} KB; mapa {'%d px' % bg_px if bg_uri else 'sin mapa (falta war_replay.py basemap --world ' + (g['world'] or '?') + ')'})")


# =====================================================================================================================
# 5) Exportar: GIF
# =====================================================================================================================
def _font(size, bold=False):
    from PIL import ImageFont
    for p in (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else []) + ["/System/Library/Fonts/Supplemental/Arial.ttf",
                                                                                          "/Library/Fonts/Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def export_gif(g, args, out):
    from PIL import Image, ImageChops, ImageDraw
    img, land, ws = load_map(args, g)
    towns = g["towns"]
    n = len(towns)
    W = args.gif_size
    #--- encuadre: los pueblos con margen (cuadrado, dentro del mapa)
    xs = [t[1] for t in towns] or [0, ws]
    ys = [t[2] for t in towns] or [0, ws]
    m = max(600.0, 0.06 * ws)
    side = max(max(xs) - min(xs), max(ys) - min(ys)) + 2 * m
    side = min(side, ws)
    cx = min(max((max(xs) + min(xs)) / 2, side / 2), ws - side / 2)
    cy = min(max((max(ys) + min(ys)) / 2, side / 2), ws - side / 2)
    x0, y1 = cx - side / 2, cy + side / 2
    k = W / side

    def P(x, y):
        return ((x - x0) * k, (y1 - y) * k)

    if img is not None:
        sc = img.width / ws
        base = img.crop((int(x0 * sc), int((ws - y1) * sc), int((x0 + side) * sc), int((ws - y1 + side) * sc))).resize((W, W), Image.LANCZOS)
    else:
        base = Image.new("RGB", (W, W), (26, 69, 112))
    #--- zonas: pueblo mas cercano en tierra (rejilla G x G)
    G = 160
    owner_of = [-1] * (G * G)
    lpx = land.load() if land is not None else None
    maxd2 = max(1500.0, ws / 32 * 4) ** 2
    for j in range(G):
        for i in range(G):
            x = x0 + (i + 0.5) / G * side
            y = y1 - (j + 0.5) / G * side
            on = True
            if lpx is not None:
                li, lj = int(x / ws * land.width), int((1 - y / ws) * land.height)
                on = 0 <= li < land.width and 0 <= lj < land.height and lpx[li, lj] >= 128
            if not on:
                continue
            best, bd = -1, maxd2 if lpx is not None else 1200.0 ** 2
            for t_i, t in enumerate(towns):
                d = (t[1] - x) ** 2 + (t[2] - y) ** 2
                if d < bd:
                    bd, best = d, t_i
            owner_of[j * G + i] = best
    col = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in SIDE_HEX]
    si = lambda s: s if s in (0, 1, 2) else 3  # noqa: E731
    HEAD, FOOT = 64, 74
    fh, fb, fs = _font(16, True), _font(15), _font(13)
    total_h = HEAD + W + FOOT
    fps = args.fps
    nfr = max(2, int(args.gif_seconds * fps))
    span = max(1, g["span"])
    clk = clock_points(g)
    counts0 = [t[3] for t in towns]

    def clock_at(t):
        if not clk:
            return ""
        kk = max(0, max([i for i, c in enumerate(clk) if c[0] <= t] or [0]))
        mm = clk[kk][1]
        if kk + 1 < len(clk) and clk[kk][0] <= t:
            f = min(1.0, (t - clk[kk][0]) / max(1, clk[kk + 1][0] - clk[kk][0]))
            mm += (clk[kk + 1][1] - mm) * max(0.0, f)
        hm = int(mm) % 1440
        return f"Día {int(mm // 1440) + 1} - {hm // 60:02d}:{hm % 60:02d}"

    frames, durs = [], []
    own = counts0[:]
    cptr = 0
    last_cap = [-1e9] * n
    names = g["sides"]
    title = "HISTORIA DE LA GUERRA" + (f" - {g['title']}" if g["title"] else "")
    win = 1.3 * span / args.gif_seconds
    pal_img = None
    for fr in range(nfr + 1):
        t = span * fr / nfr
        while cptr < len(g["changes"]) and g["changes"][cptr][0] <= t:
            ct, ti, ts = g["changes"][cptr]
            if 0 <= ti < n:
                own[ti] = ts
                last_cap[ti] = ct
            cptr += 1
        im = Image.new("RGB", (W, total_h), (22, 24, 26))
        mapim = base.copy().convert("RGBA")
        ov = Image.new("RGBA", (G, G), (0, 0, 0, 0))
        opx = ov.load()
        for p, o in enumerate(owner_of):
            if o >= 0:
                c = col[si(own[o])]
                opx[p % G, p // G] = (c[0], c[1], c[2], 118)
        mapim = Image.alpha_composite(mapim, ov.resize((W, W), Image.BILINEAR))
        d = ImageDraw.Draw(mapim)
        #--- equipos
        ks = [i for i, s in enumerate(g["snaps"]) if s[0] <= t]
        if ks:
            sp = g["snaps"][ks[-1]]
            for sd in (0, 1):
                for px_, py_ in sp[2 + sd]:
                    x, y = P(px_, py_)
                    if 0 <= x < W and 0 <= y < W:
                        d.rectangle([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=col[sd] + (255,), outline=(12, 12, 12, 220))
        #--- destellos
        for i in range(n):
            age = t - last_cap[i]
            if 0 <= age < win:
                f = age / win
                x, y = P(towns[i][1], towns[i][2])
                r = 7 + 26 * f
                d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, int(255 * (1 - f))), width=2)
        for e in g["events"]:
            if e[0] > t:
                break
            age = t - e[0]
            if age < win * 1.5 and (e[3] or e[4]) and e[1] not in ("start", "resume", "end"):
                f = age / (win * 1.5)
                x, y = P(e[3], e[4])
                r = 9 + 36 * f
                c = (255, 214, 90) if e[1] in ("cap", "af") else (255, 140, 40)
                d.ellipse([x - r, y - r, x + r, y + r], outline=c + (int(255 * (1 - f)),), width=3)
        #--- pueblos y nombres de capital / aerodromos
        for i, tw in enumerate(towns):
            x, y = P(tw[1], tw[2])
            c = col[si(own[i])] + (255,)
            r = 5.5 if tw[4] else 4.5
            if tw[4] & 1:
                poly = [(x, y - r * 1.5), (x + r * 1.5, y), (x, y + r * 1.5), (x - r * 1.5, y)]
            elif tw[4] & 2:
                poly = [(x, y - r * 1.4), (x + r * 1.3, y + r * 0.9), (x - r * 1.3, y + r * 0.9)]
            else:
                poly = None
            if poly:
                d.polygon(poly, fill=c, outline=(255, 255, 255, 255))
            else:
                d.ellipse([x - r, y - r, x + r, y + r], fill=c, outline=(255, 255, 255, 255), width=2)
            if tw[4]:
                d.text((x + r + 4, y), tw[0], font=fs, fill=(255, 255, 255, 255), anchor="lm", stroke_width=2, stroke_fill=(10, 12, 14, 255))
        im.paste(mapim.convert("RGB"), (0, HEAD))
        dd = ImageDraw.Draw(im)
        #--- cabecera: titulo, reloj y pueblos por bando
        ctext = f"{clock_at(t)}   partida {hms(t)}"
        tmax = W - 40 - dd.textlength(ctext, font=fb)
        tt = title
        if dd.textlength(tt, font=fh) > tmax:
            while len(tt) > 8 and dd.textlength(tt + "\u2026", font=fh) > tmax:
                tt = tt[:-1]
            tt = tt.rstrip() + "\u2026"
        dd.text((12, 10), tt, font=fh, fill=(255, 210, 127))
        dd.text((W - 12, 10), ctext, font=fb, fill=(235, 235, 230), anchor="ra")
        cnt = [0, 0, 0, 0]
        for s in own:
            cnt[si(s)] += 1
        xx = 12
        for s in range(4):
            label = f"{names[s] if s < 3 else 'sin dueño'}: {cnt[s]}"
            dd.rectangle([xx, 40, xx + 10, 50], fill=col[s])
            dd.text((xx + 15, 45), label, font=fb, fill=(235, 235, 230), anchor="lm")
            xx += 26 + int(dd.textlength(label, font=fb))
        #--- pie: barra de dominio, progreso y ultimo aviso
        y0 = HEAD + W + 8
        xx = 12.0
        for s in range(4):
            ww = (W - 24) * cnt[s] / max(1, n)
            if ww > 0:
                dd.rectangle([xx, y0, xx + ww - 1, y0 + 9], fill=col[s])
            xx += ww
        dd.rectangle([12, y0 + 16, W - 12, y0 + 19], fill=(70, 70, 66))
        dd.rectangle([12, y0 + 16, 12 + (W - 24) * t / span, y0 + 19], fill=(240, 179, 90))
        evs = [e for e in g["events"] if e[0] <= t]
        if evs:
            e = evs[-1]
            dd.text((12, y0 + 30), f"[{hms(e[0])}] {event_text(g, e)}"[:90], font=fb, fill=(240, 239, 236))
        if len(evs) > 1:
            e = evs[-2]
            dd.text((12, y0 + 50), f"[{hms(e[0])}] {event_text(g, e)}"[:95], font=fs, fill=(160, 158, 150))
        if pal_img is None:
            pal_img = im.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        frames.append(im.quantize(palette=pal_img, dither=Image.Dither.NONE))
        durs.append(int(1000 / fps))
    durs[-1] = 3500
    #--- cuadros delta: solo los pixeles que cambian; el resto es el indice transparente 255 (sin desechar el anterior)
    deltas = [frames[0]]
    for a_, b_ in zip(frames[:-1], frames[1:]):
        la = Image.frombytes("L", a_.size, a_.tobytes())
        lb = Image.frombytes("L", b_.size, b_.tobytes())
        mask = ImageChops.difference(la, lb).point(lambda v: 255 if v else 0)
        dl = Image.new("P", b_.size, 255)
        dl.putpalette(b_.getpalette())
        dl.paste(b_, (0, 0), mask)
        deltas.append(dl)
    deltas[0].save(out, save_all=True, append_images=deltas[1:], duration=durs, loop=0, optimize=False, disposal=1, transparency=255)
    print(f"GIF: {out} ({os.path.getsize(out) // 1024} KB; {len(frames)} cuadros de {W}x{total_h}, {fps} por s, {args.gif_seconds} s + 3,5 s al final)")


def cmd_export(args):
    games = load_games(args)
    g = pick_game(games, args.game)
    if not (args.html or args.gif):
        args.html = os.path.join(os.getcwd(), f"war_replay_{(g['mission'] or 'partida').lower()}_{(g['start'] or 'x').replace(' ', '_').replace(':', '')}.html")
    print(f"Partida: {g['title']} ({g['world']}), {g['start']}, dura {hms(g['span'])}, {len(g['towns'])} pueblos, "
          f"{len(g['changes'])} cambios, {len(g['events'])} avisos, {len(g['snaps'])} fotos")
    if args.html:
        export_html(g, args, args.html)
    if args.gif:
        export_gif(g, args, args.gif)
    return 0


# =====================================================================================================================
# 6) Perfil sintetico de ejemplo (mismo formato que el del juego) y pruebas
# =====================================================================================================================
# Pueblos de Tanoa (nombre, duenio inicial del mission.sqm, x, y): copia de tmp/towns.tsv del proyecto (2026-10-17)
TANOA_TOWNS = """Nasua w 11398 12369|Koumac r 1486 2982|Cerebu r 2142 4546|Yanukka r 2976 3355|Lailai r 3615 2131|Katkoula r 5565 4031
Savaka r 7162 4236|Laikoro r 1690 6131|Rautake r 3464 6755|Balavu r 2591 7395|Tavu r 848 7674|Muaceba r 1570 8476|Leqa r 2360 8162
Sosovu r 2653 9322|Belfort r 3164 11046|Tuvanaka r 1839 12028|Tuvanaka Airbase r 2371 13303|Tobakoro e 8817 3696|La Foa e 8953 4706
Moddergat e 9338 4014|Loesi e 10100 5017|Harcourt e 11223 5231|Blerick e 10319 2640|Lijnhaven e 11686 2768|Rereki e 13012 2140
Port-Boise e 12751 3237|Doodstil e 12832 4872|Kotomo e 10817 6328|Oumere e 12898 7338|Luganville e 13907 8325|Nandai e 14475 8907
Ba w 14290 11619|Blue Pearl Port w 13618 11994|Ovau w 12406 12668|La Rochelle Aerodrome w 11746 13096|Penelo w 10955 13177
Momea w 10355 13278|La Rochelle w 9548 13525|Savu w 8522 13725|Saint-Paul w 7962 13518|Petit Nicolet w 6793 13386|Nicolet w 6338 12766
Oua-Oue w 5698 12338|Saint-Julien w 5823 11146|Georgetown w 5900 10393|Georgetown Port w 5265 10043|Railway Depot e 4214 8459
Regina e 5103 8706|Lobaka e 6149 8571|Diesel Power Plant e 7447 8554|Lifou e 7255 7996|Lami e 7912 7610|Aeroport de Tanoa e 6867 7313
Lumberyard South e 9422 7498|Lumberyard North w 8846 11933|Tanouka w 8921 10201|Vagalala w 11021 9690|Red Spring Surface Mine w 11948 10317
Imone w 10542 10522|Comms Bravo w 11043 11555"""


def _tanoa_towns():
    out = []
    for item in TANOA_TOWNS.replace("\n", "|").split("|"):
        parts = item.strip().rsplit(" ", 3)
        name, side, x, y = parts[0], parts[1], int(parts[2]), int(parts[3])
        out.append([name, {"w": 0, "e": 1, "r": 2}[side], x, y])
    return out


def _land_checker(args):
    from PIL import Image
    _p, fland, _j = map_files(args, "tanoa")
    if not os.path.exists(fland):
        return None
    lm = Image.open(fland).convert("L")
    px = lm.load()

    def ok(x, y):
        i, j = int(x / 15360 * lm.width), int((1 - y / 15360) * lm.height)
        return 0 <= i < lm.width and 0 <= j < lm.height and px[i, j] >= 128
    return ok


def synth_war(rng, seconds, west_bias, land_ok, start_sys, start_date, title, winner_side=0, accel=6.0, finish=True):
    """Guerra inventada (plausible) en Tanoa con el formato VIOCWR1 exacto que graba el juego."""
    T = _tanoa_towns()
    n = len(T)
    flags = [0] * n
    for i, t in enumerate(T):
        if t[0] == "Georgetown":
            flags[i] = 1
        if t[0] in ("Aeroport de Tanoa", "La Rochelle Aerodrome", "Tuvanaka Airbase"):
            flags[i] = 2
    towns = [[t[0], t[2], t[3], t[1], flags[i]] for i, t in enumerate(T)]
    own = [t[1] for t in T]
    U = 10
    ch, ev, sn = [], [], []

    def add_ev(t, k, s, x, y, i):
        ev.append(f"{int(t)},{k},{s},{int(round(x / U))},{int(round(y / U))},{i}")

    add_ev(0, "start", -1, 0, 0, -1)
    bases = {0: (13300, 11800), 1: (11900, 3100)}
    pending = []  # contraataques [t, pueblo, bando]
    t = 40
    hq_done = {0: False, 1: False}
    while t < seconds:
        frac = t / seconds
        pw = min(0.92, max(0.18, west_bias(frac)))
        if pending and pending[0][0] <= t:
            _pt, i, s = pending.pop(0)
            if own[i] != s:
                own[i] = s
                ch.append(f"{int(t)},{i},{s}")
                if flags[i] & 1:
                    add_ev(t, "cap", s, T[i][2], T[i][3], i)
                if flags[i] & 2:
                    add_ev(t, "af", s, T[i][2], T[i][3], i)
            t += rng.randint(40, 110)
            continue
        r = rng.random()
        s = 2 if r < 0.05 else (0 if rng.random() < pw else 1)
        cand = []
        for i in range(n):
            if own[i] == s:
                continue
            dmin = min([((T[i][2] - T[j][2]) ** 2 + (T[i][3] - T[j][3]) ** 2) ** 0.5 for j in range(n) if own[j] == s] or [1e9])
            if s == 2 and dmin > 3500:
                continue
            cand.append((dmin * (0.7 + 0.6 * rng.random()) * (2.2 if flags[i] & 1 else 1.0), i))
        if cand:
            cand.sort()
            _d, i = cand[0]
            old = own[i]
            own[i] = s
            ch.append(f"{int(t)},{i},{s}")
            if flags[i] & 1:
                add_ev(t, "cap", s, T[i][2], T[i][3], i)
            if flags[i] & 2:
                add_ev(t, "af", s, T[i][2], T[i][3], i)
            if old in (0, 1) and rng.random() < 0.33:
                pending.append([t + rng.randint(150, 420), i, old])
                pending.sort()
        t += rng.randint(55, 160)
        #--- avisos sueltos
        if rng.random() < 0.10:
            sd = 0 if rng.random() < pw else 1
            fr = [i for i in range(n) if own[i] != sd]
            if fr:
                i = min(fr, key=lambda i: min([((T[i][2] - T[j][2]) ** 2 + (T[i][3] - T[j][3]) ** 2) for j in range(n) if own[j] == sd] or [1e18]))
                add_ev(t, rng.choice(["so", "so", "cas", "gs"]), sd, T[i][2] + rng.randint(-300, 300), T[i][3] + rng.randint(-300, 300), i if rng.random() < 0.5 else -1)
        if rng.random() < 0.025:
            sd = rng.choice([0, 1])
            add_ev(t, "base", sd, bases[sd][0] + rng.randint(-150, 150), bases[sd][1] + rng.randint(-150, 150), rng.randint(1, 2))
        loser = 1 - winner_side
        if finish and not hq_done[loser] and frac > 0.9:
            hq_done[loser] = True
            add_ev(t, "hq", loser, bases[loser][0], bases[loser][1], -1)
        if not hq_done[winner_side] and 0.45 < frac < 0.5 and rng.random() < 0.3:
            hq_done[winner_side] = True
            add_ev(t, "hq", winner_side, bases[winner_side][0], bases[winner_side][1], -1)
    #--- final: el ganador toma lo que queda
    rest = [i for i in range(n) if own[i] != winner_side] if finish else []
    for i in rest:
        own[i] = winner_side
        t += rng.randint(20, 50)
        ch.append(f"{int(t)},{i},{winner_side}")
        if flags[i] & 1:
            add_ev(t, "cap", winner_side, T[i][2], T[i][3], i)
        if flags[i] & 2:
            add_ev(t, "af", winner_side, T[i][2], T[i][3], i)
    t_end = t + 15
    if finish:
        add_ev(t_end, "end", winner_side, 0, 0, -1)
    #--- equipos: 10 por bando, cada uno va al frente y cambia de objetivo al llegar
    own2 = [tt[1] for tt in T]
    changes = [tuple(int(v) for v in c.split(",")) for c in ch]
    teams = {sd: [[bases[sd][0] + rng.randint(-400, 400), bases[sd][1] + rng.randint(-400, 400), -1] for _ in range(10)] for sd in (0, 1)}
    cp = 0
    for ts in range(10, t_end, 120):
        while cp < len(changes) and changes[cp][0] <= ts:
            own2[changes[cp][1]] = changes[cp][2]
            cp += 1
        parts = []
        for sd in (0, 1):
            pts = []
            alive = min(10, round(10 * sum(1 for o in own2 if o == sd) / max(1, n / 2.5)))  # equipos segun los pueblos
            for tm in teams[sd][:alive]:
                if tm[2] < 0 or own2[tm[2]] == sd or rng.random() < 0.08:
                    fr = [i for i in range(n) if own2[i] != sd]
                    if fr:
                        fr.sort(key=lambda i: (T[i][2] - tm[0]) ** 2 + (T[i][3] - tm[1]) ** 2)
                        tm[2] = rng.choice(fr[:4])
                if tm[2] >= 0:
                    tx, ty = T[tm[2]][2] + rng.randint(-250, 250), T[tm[2]][3] + rng.randint(-250, 250)
                    dx, dy = tx - tm[0], ty - tm[1]
                    dist = (dx * dx + dy * dy) ** 0.5
                    step = min(dist, rng.randint(500, 1300))
                    if dist > 1:
                        nx, ny = tm[0] + dx / dist * step, tm[1] + dy / dist * step
                        if land_ok is None or land_ok(nx, ny):
                            tm[0], tm[1] = nx, ny
                        elif rng.random() < 0.35:
                            tm[0], tm[1] = tx, ty  # helicoptero / barco
                pts += [int(round(tm[0] / U)), int(round(tm[1] / U))]
            parts.append(" ".join(str(v) for v in pts) if pts else "-")
        mins = (int(start_date[3]) * 60 + int(start_date[4]) + int(ts * accel / 60)) % 1440
        sn.append(f"{ts},{mins},{parts[0]},{parts[1]}")
    end_sys = list(start_sys)
    tot = int(start_sys[3]) * 60 + int(start_sys[4]) + t_end // 60
    end_sys[3], end_sys[4] = (tot // 60) % 24, tot % 60
    npos = sum(len(s.split(",")[2].split()) // 2 + len(s.split(",")[3].split()) // 2 for s in sn)
    meta = ["VIOBECTICW_RHS_US_RU_tanoa", "Tanoa", 15360.0, title, list(start_sys), list(start_date), ["EE.UU.", "Rusia", "Guerrilla"], "war_replay 2026-10-17 (sintetico)", 10.0]
    status = [float(t_end), 1.0 if finish else 0.0, float(winner_side) if finish else -1.0, end_sys if finish else [], list(start_date), float(npos), float(len(ch)), float(len(ev)), 0.0, 120.0]
    return [TAG, meta, towns, ";".join(ch) + ";", ";".join(ev) + ";", ";".join(sn) + ";", status]


def cmd_sample(args):
    rng = random.Random(args.seed)
    land_ok = _land_checker(args)
    war1 = synth_war(rng, 11000, lambda f: 0.5 - 0.2 * math.sin(min(1, f / 0.55) * math.pi) + 0.35 * max(0.0, f - 0.55) / 0.45,
                     land_ok, [2026, 10, 15, 20, 10, 0, 0], [2035, 6, 14, 6, 0], "VIO-BECTI-CW Tanoa (RHS) OTAN vs Rusia", winner_side=0)
    war2 = synth_war(rng, 4200, lambda f: 0.42 - 0.15 * f, land_ok, [2026, 10, 16, 21, 30, 0, 0], [2035, 6, 14, 18, 0],
                     "VIO-BECTI-CW Tanoa (RHS) OTAN vs Rusia", winner_side=1)
    cur = synth_war(rng, 1500, lambda f: 0.55, land_ok, [2026, 10, 17, 19, 5, 0, 0], [2035, 6, 14, 6, 0],
                    "VIO-BECTI-CW Tanoa (RHS) OTAN vs Rusia", winner_side=0, finish=False)
    key = "VIOC_WAR_VIOBECTICW_RHS_US_RU_tanoa_Tanoa"
    variables = {
        "bis_welcomescreenportshown": 1.0,                 # como en el perfil real: numeros, textos, logicos, vacios
        "gui_bcg_rgb_presetdefault": "PresetRCgold",
        "cti_persistent_hints": True,
        "save_viobecticw_us_ru_malden_west_fobs": [],
        key: cur,
        key + "_HIST": [war1, war2],               # como en el juego: la mas vieja primero
    }
    out = args.out or os.path.join(HERE, "sample", "sample.vars.Arma3Profile")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    size = write_profile(out, variables)
    print(f"perfil sintetico: {out} ({size // 1024} KB): partida en curso de {hms(cur[6][0])} y 2 terminadas "
          f"({hms(war2[6][0])} gana Rusia, {hms(war1[6][0])} gana EE.UU.); tierra {'del mapa guardado' if land_ok else 'sin mascara'}")
    return 0


def cmd_dump(args):
    variables = read_profile(args.profile or DEFAULT_PROFILE)
    pat = (args.grep or "").lower()
    for name in sorted(variables):
        if pat and pat not in name:
            continue
        v = variables[name]
        desc = f"lista de {len(v)}" if isinstance(v, list) else type(v).__name__
        print(f"{name}: {desc}")
    print(f"{len(variables)} variables")
    return 0


def cmd_selftest(args):
    ok = True
    rng = random.Random(3)
    #--- 1) ida y vuelta: escritor -> lector (los numeros pasan por float32)
    import tempfile
    rec = synth_war(rng, 2400, lambda f: 0.5, None, [2026, 1, 2, 3, 4, 5, 6], [2035, 6, 14, 23, 50], "prueba")
    variables = {"a_num": 3.25, "a_str": "hola, mundo; \"comillas\"", "a_bool": False, "a_empty": [], "nested": [1.0, ["x", [2.0, True]], []],
                 "VIOC_WAR_PRUEBA_Tanoa": rec, "VIOC_WAR_PRUEBA_Tanoa_HIST": [rec, rec]}
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "t.vars.Arma3Profile")
        write_profile(p, variables)
        back = read_profile(p)
    ok &= _check("nombres en minusculas", set(back) == {k.lower() for k in variables})
    ok &= _check("numero / texto / logico / vacio", back["a_num"] == 3.25 and back["a_str"] == variables["a_str"] and back["a_bool"] is False and back["a_empty"] == [])
    ok &= _check("arreglos anidados", back["nested"] == [1.0, ["x", [2.0, True]], []])
    g = decode_record(back["vioc_war_prueba_tanoa"], "x")
    g0 = decode_record(rec, "x")
    ok &= _check("registro VIOCWR1 igual tras el perfil", g is not None and g0 is not None and
                 all(g[k] == g0[k] for k in ("towns", "changes", "events", "snaps", "span", "winner", "finished")))
    ok &= _check("historial con 2 partidas", isinstance(back["vioc_war_prueba_tanoa_hist"], list) and len(back["vioc_war_prueba_tanoa_hist"]) == 2)
    ok &= _check("dia 2 en el reloj (cruza la medianoche)", g is not None and any(c[1] >= 1440 for c in clock_points(g)))
    #--- 2) texto SQF (copyToClipboard str VIOC_WR_DATA)
    sqf = '["VIOCWR1",["m","Tanoa",15360,"T",[2026,10,17,1,2,3,4],[2035,6,14,6,0],["A","B","C"],"v",10],[["Ge""o",5900,10393,0,1]],"35,0,1;","0,start,-1,0,0,-1;","10,360,590 1039,-;",[35,0,-1,[],[],1,1,1,0,120]]'
    gs = decode_record(parse_sqf(sqf), "sqf")
    ok &= _check("texto SQF", gs is not None and gs["towns"][0][0] == 'Ge"o' and gs["changes"] == [[35, 0, 1]] and gs["snaps"][0][2] == [[5900, 10390]])
    #--- 3) tiempos grandes en float32 (los cambios van como texto; el estado como numero)
    ok &= _check("t = 999999 s exacto en float32", struct.unpack("<f", struct.pack("<f", 999999.0))[0] == 999999.0)
    #--- 4) el perfil real (SOLO LECTURA)
    rp = args.profile or DEFAULT_PROFILE
    if os.path.exists(rp):
        before = os.path.getmtime(rp)
        rv = read_profile(rp)
        mine = sorted(k for k in rv if k.startswith(KEY_PREFIX))
        print(f"  perfil real: {len(rv)} variables leidas; partidas war_replay: {mine or 'ninguna todavia'}")
        ok &= _check("perfil real sin tocar", os.path.getmtime(rp) == before)
        ok &= _check("perfil real leido sin errores", len(rv) > 0)
    else:
        print(f"  (no hay perfil real en {rp})")
    print("selftest:", "OK" if ok else "FALLA")
    return 0 if ok else 1


def _check(name, cond):
    print(f"  [{'OK' if cond else 'FALLA'}] {name}")
    return bool(cond)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Historia de la guerra (VIO-BECTI-CW war_replay): lista y exporta las partidas grabadas")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def src(p):
        p.add_argument("--profile", help="perfil .vars.Arma3Profile (por defecto el del usuario; solo lectura)")
        p.add_argument("--sqf", help="texto de copyToClipboard str VIOC_WR_DATA (en vez del perfil)")
        p.add_argument("--maps", help="carpeta de mapas guardados (por defecto war_replay_maps junto al script)")

    p = sub.add_parser("list", help="partidas grabadas")
    src(p)
    p = sub.add_parser("export", help="exporta una partida a HTML y/o GIF")
    src(p)
    p.add_argument("--game", type=int, help="numero de la lista (por defecto la ultima terminada)")
    p.add_argument("--html", help="archivo HTML de salida")
    p.add_argument("--gif", help="archivo GIF de salida")
    p.add_argument("--seconds", type=int, default=60, help="duracion de la repeticion en el HTML (30/60/120/300)")
    p.add_argument("--gif-seconds", type=float, default=24.0, help="duracion del GIF")
    p.add_argument("--fps", type=int, default=10, help="cuadros por segundo del GIF")
    p.add_argument("--gif-size", type=int, default=720, help="ancho del mapa del GIF en pixeles")
    p.add_argument("--names", help="nombres de los bandos 'oeste,este,resistencia' (por defecto los grabados)")
    p = sub.add_parser("basemap", help="pinta y guarda el mapa de un terreno (numpy + tools/vio_wrp.py)")
    p.add_argument("--world", required=True)
    p.add_argument("--pbo", help="PBO del terreno (con el .wrp)")
    p.add_argument("--size", type=int, default=2048)
    p.add_argument("--maps")
    p = sub.add_parser("sample", help="escribe un perfil sintetico con partidas inventadas (mismo formato)")
    p.add_argument("--out")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--maps")
    p = sub.add_parser("selftest", help="pruebas del formato y lectura del perfil real (sin tocarlo)")
    p.add_argument("--profile")
    p = sub.add_parser("dump", help="variables del perfil")
    p.add_argument("--profile")
    p.add_argument("--grep")
    a = ap.parse_args(argv)
    return {"list": cmd_list, "export": cmd_export, "basemap": cmd_basemap, "sample": cmd_sample, "selftest": cmd_selftest, "dump": cmd_dump}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
