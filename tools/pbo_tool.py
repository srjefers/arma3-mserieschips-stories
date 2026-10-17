#!/usr/bin/env python3
"""pbo_tool.py — herramienta mínima para PBOs de Arma 3 (solo librería estándar de Python).

Uso:
  pbo_tool.py list    <pbo>                        lista entradas y valida el checksum
  pbo_tool.py verify  <pbo>                        valida estructura + SHA1 (exit 1 si falla)
  pbo_tool.py extract <pbo> <entrada> <destino>    extrae una entrada (acepta / o \\)
  pbo_tool.py unpack  <pbo> <carpeta>              extrae todo (para inspección)
  pbo_tool.py patch   <in.pbo> <out.pbo> <entrada>=<archivo> [...]
        crea out.pbo idéntico a in.pbo salvo las entradas reemplazadas
        (mismo orden, cabeceras y datos) y recalcula el SHA1 final
  pbo_tool.py diff    <a.pbo> <b.pbo>              lista entradas distintas

Nunca sobrescribe archivos existentes. No soporta entradas comprimidas (las detecta y aborta).
Formato: https://community.bistudio.com/wiki/PBO_File_Format
"""
import hashlib
import os
import struct
import sys
import time

VERS = 0x56657273  # 'Vers': entrada de producto con propiedades (prefix, etc.)
CPRS = 0x43707273  # 'Cprs': entrada comprimida
HDR = struct.Struct("<5I")  # packing method, original size, reserved, timestamp, data size


class Pbo:
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.data = f.read()
        self.prefix = b""  # bytes crudos de la entrada 'Vers' + propiedades, si existe
        self.props = []
        self.entries = []
        self._parse()

    def _asciiz(self, pos):
        end = self.data.index(b"\0", pos)
        return self.data[pos:end].decode("latin-1"), end + 1

    def _parse(self):
        pos = 0
        while True:
            start = pos
            name, pos = self._asciiz(pos)
            method, orig, reserved, ts, size = HDR.unpack_from(self.data, pos)
            pos += HDR.size
            if name == "" and method == VERS and not self.entries:
                while True:
                    key, pos = self._asciiz(pos)
                    if key == "":
                        break
                    value, pos = self._asciiz(pos)
                    self.props.append((key, value))
                self.prefix = self.data[start:pos]
                continue
            if name == "":
                self.terminator = self.data[start:pos]
                break
            self.entries.append(dict(name=name, method=method, orig=orig, reserved=reserved,
                                     ts=ts, size=size, header=self.data[start:pos]))
        for e in self.entries:
            e["offset"] = pos
            pos += e["size"]
        if pos > len(self.data):
            raise ValueError(f"{self.path}: PBO truncado")
        self.body_end = pos
        tail = self.data[pos:]
        self.sha1_ok = (len(tail) == 21 and tail[0] == 0
                        and tail[1:] == hashlib.sha1(self.data[:pos]).digest())

    def raw(self, e):
        return self.data[e["offset"]:e["offset"] + e["size"]]

    def find(self, name):
        key = name.replace("/", "\\").lower()
        for e in self.entries:
            if e["name"].lower() == key:
                return e
        raise KeyError(f"{self.path}: no existe la entrada {name!r}")

    @staticmethod
    def is_compressed(e):
        return e["method"] == CPRS or e["orig"] not in (0, e["size"])

    def content(self, e):
        if self.is_compressed(e):
            raise ValueError(f"{e['name']}: entrada comprimida (no soportada)")
        return self.raw(e)


def write_new(dest, data):
    if os.path.exists(dest):
        sys.exit(f"ERROR: {dest} ya existe (no sobrescribo)")
    with open(dest, "wb") as f:
        f.write(data)


def build_pbo(entries, props=()):
    """Bytes de un PBO nuevo sin comprimir. entries: [(nombre con \\, bytes, timestamp)];
    props: [(clave, valor)] de la entrada 'Vers' (p. ej. ("prefix", "mi_addon"))."""
    out = bytearray(b"\0" + HDR.pack(VERS, 0, 0, 0, 0))
    for k, v in props:
        out += k.encode("latin-1") + b"\0" + v.encode("latin-1") + b"\0"
    out += b"\0"
    for name, data, ts in entries:
        out += name.encode("latin-1") + b"\0" + HDR.pack(0, 0, 0, int(ts), len(data))
    out += b"\0" + HDR.pack(0, 0, 0, 0, 0)
    for _, data, _ in entries:
        out += data
    out += b"\0" + hashlib.sha1(out).digest()
    return bytes(out)


def cmd_list(path):
    p = Pbo(path)
    print(f"{path}\n  propiedades: {p.props}\n  entradas: {len(p.entries)}  comprimidas: "
          f"{sum(map(Pbo.is_compressed, p.entries))}  SHA1 ok: {p.sha1_ok}")
    for e in p.entries:
        print(f"  {e['size']:>9}  {e['name']}")


def cmd_verify(path):
    p = Pbo(path)
    comp = sum(map(Pbo.is_compressed, p.entries))
    print(f"{path}: {len(p.entries)} entradas, {comp} comprimidas, SHA1 {'OK' if p.sha1_ok else 'INVALIDO'}")
    return 0 if p.sha1_ok else 1


def cmd_extract(path, entry, dest):
    p = Pbo(path)
    write_new(dest, p.content(p.find(entry)))


def cmd_unpack(path, folder):
    p = Pbo(path)
    for e in p.entries:
        dest = os.path.join(folder, *e["name"].split("\\"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        write_new(dest, p.content(e))
    print(f"{len(p.entries)} archivos extraídos en {folder}")


def cmd_patch(src, dst, specs):
    p = Pbo(src)
    if not p.sha1_ok:
        sys.exit(f"ERROR: {src} tiene checksum inválido")
    repl = {}
    for spec in specs:
        entry, sep, local = spec.partition("=")
        if not sep:
            sys.exit(f"ERROR: formato esperado <entrada>=<archivo>: {spec}")
        with open(local, "rb") as f:
            repl[p.find(entry)["name"]] = f.read()
    out = bytearray(p.prefix)
    for e in p.entries:
        if e["name"] in repl:
            new = repl[e["name"]]
            orig = len(new) if e["orig"] else 0  # respeta la convención del PBO original
            out += e["name"].encode("latin-1") + b"\0"
            out += HDR.pack(0, orig, e["reserved"], int(time.time()), len(new))
        else:
            out += e["header"]
    out += p.terminator
    for e in p.entries:
        out += repl[e["name"]] if e["name"] in repl else p.raw(e)
    out += b"\0" + hashlib.sha1(out).digest()
    write_new(dst, bytes(out))
    print(f"{dst}: {len(repl)} entrada(s) reemplazada(s) de {len(p.entries)}")


def cmd_diff(a, b):
    pa, pb = Pbo(a), Pbo(b)
    na = {e["name"].lower(): e for e in pa.entries}
    nb = {e["name"].lower(): e for e in pb.entries}
    for n in sorted(na.keys() - nb.keys()):
        print(f"  solo en A: {na[n]['name']}")
    for n in sorted(nb.keys() - na.keys()):
        print(f"  solo en B: {nb[n]['name']}")
    common = sorted(na.keys() & nb.keys())
    changed = [na[n]["name"] for n in common if pa.raw(na[n]) != pb.raw(nb[n])]
    for n in changed:
        print(f"  distinto:  {n}")
    print(f"  {len(common) - len(changed)} entradas idénticas, {len(changed)} distintas")


def main(argv):
    cmds = {"list": (cmd_list, 1), "verify": (cmd_verify, 1), "extract": (cmd_extract, 3),
            "unpack": (cmd_unpack, 2), "diff": (cmd_diff, 2)}
    if len(argv) >= 5 and argv[1] == "patch":
        return cmd_patch(argv[2], argv[3], argv[4:])
    if len(argv) >= 2 and argv[1] in cmds and len(argv) - 2 == cmds[argv[1]][1]:
        return cmds[argv[1]][0](*argv[2:])
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
