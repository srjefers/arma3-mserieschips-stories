#!/usr/bin/env python3
"""vio_config.py — crea una copia configurada de una misión VIO-BECTI (no toca el original).

Copia la misión (carpeta desempacada o PBO) a una carpeta NUEVA, cambia los valores por defecto
de los parámetros del lobby en Rsc/Parameters.hpp y le pone otro nombre visible
(Rsc/Game.hpp y mission.sqm) para distinguirla en la lista de Host Server.

Uso:
  vio_config.py --src <carpeta|pbo> --out <carpeta_nueva> --name "Nombre visible" \\
                --set CTI_AI_TEAMS_ENABLED=6 --set CTI_TOWNS_RESISTANCE=4 ...
Nunca sobrescribe: si --out ya existe, aborta. Solo acepta valores que estén en values[] del parámetro.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_ci(root, rel):
    """Ruta real de 'rel' dentro de root sin distinguir mayúsculas (las misiones mezclan Rsc/RSC)."""
    cur = root
    for part in rel.split("/"):
        names = {n.lower(): n for n in os.listdir(cur)}
        if part.lower() not in names:
            sys.exit(f"ERROR: no encuentro {rel} en {root}")
        cur = os.path.join(cur, names[part.lower()])
    return cur


def param_blocks(text):
    """(nombre, inicio, fin) de cada 'class X { ... };' de primer nivel dentro de class Params."""
    out = []
    for m in re.finditer(r"class\s+(\w+)\s*\{", text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append((m.group(1), m.start(), i))
    return out


def labels(block):
    vals = re.search(r"values\[\]\s*=\s*\{(.*?)\}", block, re.S)
    texts = re.search(r"texts\[\]\s*=\s*\{(.*?)\}", block, re.S)
    v = [x.strip() for x in vals.group(1).split(",")] if vals else []
    t = re.findall(r'"(.*?)"', texts.group(1)) if texts else []
    return v, (t if len(t) == len(v) else [""] * len(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="CLASE=VALOR")
    a = ap.parse_args()

    if os.path.exists(a.out):
        sys.exit(f"ERROR: ya existe {a.out}")
    if os.path.isdir(a.src):
        shutil.copytree(a.src, a.out)
    else:
        subprocess.run([sys.executable, os.path.join(HERE, "pbo_tool.py"), "unpack", a.src, a.out],
                       check=True, stdout=subprocess.DEVNULL)

    ppath = find_ci(a.out, "Rsc/Parameters.hpp")
    text = open(ppath, encoding="utf-8", errors="surrogateescape", newline="").read()
    wanted = dict(s.split("=", 1) for s in a.set)
    changes = []
    # De atrás hacia adelante para que los índices sigan valiendo al reemplazar.
    for name, start, end in sorted(param_blocks(text), key=lambda b: -b[1]):
        if name not in wanted:
            continue
        block = text[start:end]
        v, t = labels(block)
        new = wanted.pop(name)
        if new not in v:
            sys.exit(f"ERROR: {name}={new} no está entre los valores {v}")
        m = re.search(r"(default\s*=\s*)([^;]+)(;)", block)
        old = m.group(2).strip()
        title = re.search(r'title\s*=\s*(".*?"|\$\w+)', block).group(1).strip('"')
        block = block[:m.start(2)] + new + block[m.end(2):]
        text = text[:start] + block + text[end:]
        changes.append((title, t[v.index(old)] if old in v else old, t[v.index(new)]))
    if wanted:
        sys.exit(f"ERROR: parámetros no encontrados: {', '.join(wanted)}")
    open(ppath, "w", encoding="utf-8", errors="surrogateescape", newline="").write(text)

    for rel, pat in (("Rsc/Game.hpp", r'((?:onLoadName|briefingName)\s*=\s*")[^"]*(")'),
                     ("mission.sqm", r'(briefingName\s*=\s*")[^"]*(")')):
        p = find_ci(a.out, rel)
        s = open(p, encoding="utf-8", errors="surrogateescape", newline="").read()
        s, n = re.subn(pat, lambda m: m.group(1) + a.name + m.group(2), s)
        if not n:
            sys.exit(f"ERROR: no encontré el nombre en {rel}")
        open(p, "w", encoding="utf-8", errors="surrogateescape", newline="").write(s)

    print(f"Copia creada: {a.out}\nNombre visible: {a.name}\nParámetros cambiados (valor por defecto):")
    for title, old, new in reversed(changes):
        print(f"  - {title}: {old} -> {new}")


if __name__ == "__main__":
    main()
