#!/usr/bin/env python3
"""vio_port.py — genera la misión base de VIO-BECTI-CW para un terreno nuevo (port) y la valida.

Parte de la misión CW Malden 2.0.6 del Workshop (2974799676), sin tocarla: copia sus 551 archivos y solo
regenera mission.sqm (pueblos, campamentos, defensas, puntos de aparición, marcadores de inicio de las bases,
zonas de espera y prisión). Los datos curados de cada terreno están en tools/vio_port_terrains.json.
Después, tools/vio_build.py arma los escenarios configurados sobre esta base (fuente de tipo "path").

Uso:
  vio_port.py selftest                     ida y vuelta + check de los 6 mission.sqm CW (solo defectos conocidos)
  vio_port.py survey <terreno>             datos del terreno para curar el JSON (etiquetas, islas, sitios); no escribe
  vio_port.py plan <terreno> [--generic-starts K]
                                           pueblos, depósitos, inicios, plantillas y simulación; no escribe nada
  vio_port.py build <terreno> [--version N] [--generic-starts K]
                                           work/vio_port/VIOBECTICW_<KEY>[_vN].<mundo>/ + work/vio_port/<key>_report.json
  vio_port.py check <carpeta> [--terrain <terreno>] [--json salida.json]
                                           validador independiente (estructura, semántica, geometría, archivos)
  vio_port.py sim <carpeta> [--terrain <terreno>]
                                           solo la simulación del sorteo de inicios (Init_Server.sqf + start_near_front)
Solo lee el Workshop y el juego. Nunca escribe fuera de work/vio_port/ ni sobrescribe una carpeta existente.

Code layout: 1) terrain reading (heights, objects, roads)  2) spatial helpers  3) generator  4) mission.sqm
rebuild  5) validator (separate code path: it re-reads the output and never calls the generator)
6) start simulation (used by the validator)  7) commands.
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import shutil
import struct
import sys
import time
from collections import Counter, deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
WORKSHOP = os.path.expanduser("~/Library/Application Support/Steam/steamapps/workshop/content/107410")
TERRAINS_JSON = os.path.join(HERE, "vio_port_terrains.json")
OUT_ROOT = os.path.join(PROJECT, "work", "vio_port")

sys.path.insert(0, HERE)
import vio_sqm as SQM  # noqa: E402
import vio_wrp as WRP  # noqa: E402
from pbo_tool import Pbo  # noqa: E402

# Pristine template: VIO-BECTI-CW Malden V2.0.6 (review: never Tanoa (broken Zeus) nor Takistan/Stratis (RACS=2)).
TEMPLATE_WS = "2974799676"
TEMPLATE_ENTRIES = 551
TEMPLATE_SQM_SHA1 = "084aa6ddf49b60f9b7cc7abc4585a51ecacc01a7"

# The 6 CW 2.0.6 missions used by selftest (Workshop id, worldName). Chernarus Summer (3180120014) left the
# set on 2026-10-16: the user dropped the Chernarus scenarios and unsubscribes it.
CW_REFERENCE = [("Malden", "2974799676"), ("Altis", "1758094892"), ("Takistan", "3180125933"),
                ("Enoch", "2974800207"), ("Tanoa", "2974799271"), ("Stratis", "2974798605")]
# Defects of the author's missions that `check` must find (and nothing else at ERROR level).
KNOWN_DEFECTS = {
    "Malden": {("C_ATL", "LocationCamp_F id=1488")},
    "Altis": {("B_ORPHAN", "defense id=2911")} | {("B_ORPHAN_SPAWNS", "12")},
    "Enoch": {("B_ORPHAN_SPAWNS", "2")},
    "Tanoa": {("B_ZEUS", "VIOC_ZEUS")},
}

TOWN_INIT_RE = re.compile(r'^call\{nullReturn = \[this, "([^"]*)", (resistance|west|east), (\d+), (\d+), (\d+)(?:, (\d+))?\] '
                          r'execVM "Common\\Init\\Init_Location\.sqf"\}$')
DEFENSE_KINDS = {"MG", "AT", "AA", "Mortar", "Artillery", "RADAR", "SAM"}
SPAWN_RE = re.compile(r"^cti-spawn(-west|-east)?(\d+)$")
TIERS = {"L": (30, 120, 1200), "M": (30, 90, 900), "S": (30, 60, 600)}


def say(*a):
    print(*a, flush=True)


# =====================================================================================================
# 1) TERRAIN READING: heights (vio_wrp), objects and road net (OPRW v24/v25, parsed here, read-only)
# =====================================================================================================

def _asciiz(b, p):
    e = b.index(b"\0", p)
    return b[p:e].decode("latin-1"), e + 1


def read_wrp(pbo_path):
    """Full OPRW parse: dict(size, elev, models, objects (structured array), road_parts, version).
    Layout after the elevation (checked on CWA Everon, v25): materials (asciiz + 1 byte each), model paths,
    classed models (class, model, xyz, uint32), quadtree, sizeOfObjects, quadtree, sizeOfMapInfo,
    LZO persistent[layer], LZO subdivHints[map], maxObjectId, roadNetSize, road net, objects (60 B each), map info."""
    name, b = WRP.read_entry(pbo_path, ".wrp")
    if b is None or b[:4] != b"OPRW":
        raise ValueError(f"{pbo_path}: no trae un .wrp OPRW")
    ver = struct.unpack_from("<I", b, 4)[0]
    p = 12 if ver >= 25 else 8
    lx, ly, tx, ty = struct.unpack_from("<4I", b, p)
    p += 16
    cell = struct.unpack_from("<f", b, p)[0]
    p += 4
    p = WRP._skip_quadtree(b, p)
    p = WRP._skip_quadtree(b, p)
    npk = struct.unpack_from("<I", b, p)[0]
    p += 4 + 12 * npk
    p = WRP._skip_quadtree(b, p)
    _, p = WRP._compressed(b, p, tx * ty)
    _, p = WRP._compressed(b, p, tx * ty)
    raw, p = WRP._compressed(b, p, tx * ty * 4)
    elev = np.frombuffer(raw, "<f4").reshape(ty, tx).astype(np.float32)
    nmat = struct.unpack_from("<I", b, p)[0]
    p += 4
    for _ in range(nmat):
        _, p = _asciiz(b, p)
        p += 1
    nmod = struct.unpack_from("<I", b, p)[0]
    p += 4
    models = []
    for _ in range(nmod):
        s, p = _asciiz(b, p)
        models.append(s)
    ncls = struct.unpack_from("<I", b, p)[0]
    p += 4
    for _ in range(ncls):
        _, p = _asciiz(b, p)
        _, p = _asciiz(b, p)
        p += 16
    p = WRP._skip_quadtree(b, p)
    size_objects = struct.unpack_from("<I", b, p)[0]
    p += 4
    p = WRP._skip_quadtree(b, p)
    size_mapinfo = struct.unpack_from("<I", b, p)[0]
    p += 4
    _, p = WRP._compressed(b, p, lx * ly)
    _, p = WRP._compressed(b, p, tx * ty)
    p += 4                                                    # maxObjectId
    roadnet_size = struct.unpack_from("<I", b, p)[0]
    p += 4
    if len(b) - p != roadnet_size + size_objects + size_mapinfo or size_objects % 60:
        raise ValueError(f"{name}: estructura OPRW v{ver} inesperada (objetos/caminos no cuadran)")
    end = p + roadnet_size
    parts = []
    while p < end:
        n = struct.unpack_from("<I", b, p)[0]
        p += 4
        for _ in range(n):
            npos = struct.unpack_from("<H", b, p)[0]
            p += 2
            pts = struct.unpack_from("<%df" % (3 * npos), b, p)
            p += 12 * npos + npos + 4
            path, p = _asciiz(b, p)
            p += 48
            parts.append((path, [(pts[3 * i], pts[3 * i + 2]) for i in range(npos)]))
    objs = np.frombuffer(b, dtype=np.dtype([("id", "<u4"), ("mi", "<u4"), ("m", "<f4", (12,)), ("sp", "<u4")]),
                         count=size_objects // 60, offset=p)
    return dict(version=ver, size=lx * cell, elev=elev, models=models, objects=objs, road_parts=parts, source=name)


# Obstacle model classes (model path, lower case). Radius = metres around the object's centre that a depot,
# camp or static must keep clear (conservative: half the footprint diagonal of the bigger CWA/A2 buildings).
OBSTACLE_IGNORE = ("cluttercutter", "\\a2_plant\\", "dandelion", "plantain", "cabbage", "\\clutter\\", "phragmites",
                   "road_cwa_invisible", "\\roads2\\", "\\roads\\", "asfaltka", "misc_trunk_water", "ground_garbage",
                   "\\buoy")
WALL_KEYS = ("plot_", "wall_", "\\zed", "_zed", "ohrada", "pletivo", "newplot", "plutek", "statek_plot", "brana",
             "branka", "vrat", "gate_", "zavora", "hrobecek", "bozi_muka")
BUILDING_RADIUS = {
    "kostel": 16, "kostel3": 14, "cwa_kostelik": 8, "cwa_kaple": 4, "cwa_zvonice": 5, "cwa_hospital": 24,
    "stodola_old_open": 12, "stodola_open": 12, "statek_hl_bud": 12, "statek_kulna": 9, "cwa_repair_center": 16,
    "cwa_budova1": 11, "cwa_budova2": 11, "cwa_budova3": 11, "cwa_budova4_in": 11, "cwa_budova5": 9,
    "dum_mesto": 9, "dum_mesto2": 9, "dum_mesto2l": 9, "cwa_dum_mesto3": 10, "dum_mesto_in": 9, "dum01": 8,
    "cwa_dum02": 8, "dum_rasovna": 8, "dum_m2": 8, "dum_olezlina": 8, "cwa_hospoda_mesto": 11,
    "cwa_fuelstation": 13, "garaz": 7, "vez": 5, "cwa_hlaska": 5, "bouda1": 4, "bouda2_vnitrek": 5, "bouda3": 4,
    "psi_bouda": 2, "majak": 7, "cwa_helfenburk": 26, "cwa_helfenburk_zed": 12, "cwa_helfenburk_cimburi": 12,
    "cwa_helfenburk_budova2": 10, "cwa_helfenburk_brana": 8, "molo_krychle": 10, "molo_beton": 12,
    "molo_drevo_bs": 10, "stanice": 12, "cwa_ammostore2": 10, "cwa_ryb_domek": 6, "misc_greenhouse": 6,
    "cwa_dumruina": 8, "dumruina_mini": 6, "shed_m02": 5, "ind_timbers": 8, "cwa_kasna": 3, "heli_h_rescue": 6,
    "misc_haystack": 3, "stoh": 4, "delo": 2,
}
TREE_KEYS = ("\\tree\\", "a2_tree", "str jedle", "cwa_larch", "silverspruce", "les_dub", "klady_smrk")
BUSH_KEYS = ("\\bush\\", "a2_bush", "krovi", "ker deravej")


def classify_model(path):
    """(kind, radius) of a terrain object model; kind None = ignored (clutter, roads, decals, water props)."""
    p = path.lower()
    base = p.rsplit("\\", 1)[-1].rsplit(".", 1)[0]
    if any(k in p for k in OBSTACLE_IGNORE):
        return None, 0.0
    if "runway_edgelight" in p or "runway_papi" in p or "naviglight" in p:
        return "small", 1.0
    if "runway_" in p:
        return "pavement", 20.0 if "taxi" in base else 40.0   # 40 m wide runway: keep camps/statics off the wing path
    if "t_stub" in base:
        return "tree", 1.0
    if "fallentree" in base or "trunk_torzo" in base:
        return "tree", 4.0
    if any(k in p for k in TREE_KEYS):
        return "tree", 3.0
    if any(k in p for k in BUSH_KEYS):
        return "bush", 2.0
    if "snappond" in base:
        return "pond", 26.0 if "50" in base else 13.0
    if "skala" in base:
        return "rock", 10.0
    if "r2_boulder" in base:
        return "rock", 3.0
    if "r2_stone" in base:
        return "rock", 1.5
    if base in BUILDING_RADIUS:
        return "building", float(BUILDING_RADIUS[base])
    if any(k in p for k in WALL_KEYS):
        return "wall", 4.0
    if "boatsmall" in base:
        return "small", 4.0
    if "powlines" in p or "\\signs" in p or "\\misc" in p or "misc_e\\" in p or "structures_e\\misc" in p \
            or "furniture" in p or "\\signs2\\" in p:
        return "small", 1.5
    if "\\buildings" in p or "\\structures" in p or "cwa_buildings" in p:
        return "building", 10.0
    return "small", 1.5


class PointGrid:
    """Bucket grid over circles (x, y, radius) for fast clearance / count queries."""

    def __init__(self, x, y, r, cell=32.0):
        x, y, r = (np.asarray(v, dtype=float).ravel() for v in (x, y, r))
        self.cell = float(cell)
        ix = np.floor(x / cell).astype(np.int64) + 1024
        iy = np.floor(y / cell).astype(np.int64) + 1024
        key = ix * 4096 + iy
        o = np.argsort(key, kind="stable")
        self.key, self.x, self.y, self.r = key[o], x[o], y[o], r[o]
        self.rmax = float(r.max()) if len(r) else 0.0
        self.n = len(x)

    def _ranges(self, px, py, R):
        c = self.cell
        j0 = int(math.floor((py - R) / c)) + 1024
        j1 = int(math.floor((py + R) / c)) + 1024
        for i in range(int(math.floor((px - R) / c)) + 1024, int(math.floor((px + R) / c)) + 1025):
            a = np.searchsorted(self.key, i * 4096 + j0, "left")
            b = np.searchsorted(self.key, i * 4096 + j1, "right")
            if b > a:
                yield a, b

    def clearance(self, px, py, cap=40.0):
        """Smallest (distance - radius) to any item, capped at `cap` (only items that can be closer are scanned)."""
        best = cap
        for a, b in self._ranges(px, py, cap + self.rmax):
            d = np.hypot(self.x[a:b] - px, self.y[a:b] - py) - self.r[a:b]
            m = float(d.min())
            if m < best:
                best = m
        return best

    def count(self, px, py, R):
        n = 0
        for a, b in self._ranges(px, py, R):
            n += int((np.hypot(self.x[a:b] - px, self.y[a:b] - py) <= R).sum())
        return n


class SegmentGrid:
    """Road centre lines (x1, y1, x2, y2) bucketed by midpoint."""

    def __init__(self, segs, cell=32.0):
        self.s = np.asarray(segs, dtype=float).reshape(-1, 4)
        mx = (self.s[:, 0] + self.s[:, 2]) / 2
        my = (self.s[:, 1] + self.s[:, 3]) / 2
        half = np.hypot(self.s[:, 2] - self.s[:, 0], self.s[:, 3] - self.s[:, 1]) / 2
        self.grid = PointGrid(mx, my, half, cell)
        o = np.argsort((np.floor(mx / cell).astype(np.int64) + 1024) * 4096 + np.floor(my / cell).astype(np.int64) + 1024,
                       kind="stable")
        self.s = self.s[o]

    def dist(self, px, py, cap=300.0):
        """Distance to the nearest road centre line (cap if none within cap)."""
        if self.grid.n == 0:
            return cap
        best = cap
        for a, b in self.grid._ranges(px, py, cap + self.grid.rmax):
            s = self.s[a:b]
            vx, vy = s[:, 2] - s[:, 0], s[:, 3] - s[:, 1]
            L2 = np.maximum(vx * vx + vy * vy, 1e-9)
            t = np.clip(((px - s[:, 0]) * vx + (py - s[:, 1]) * vy) / L2, 0, 1)
            d = float(np.hypot(px - (s[:, 0] + t * vx), py - (s[:, 1] + t * vy)).min())
            if d < best:
                best = d
        return best

    def nearest_dir(self, px, py, cap=80.0):
        """Direction (deg, 0 = north) of the nearest road segment, or None."""
        best, bd = None, cap
        for a, b in self.grid._ranges(px, py, cap + self.grid.rmax):
            s = self.s[a:b]
            vx, vy = s[:, 2] - s[:, 0], s[:, 3] - s[:, 1]
            L2 = np.maximum(vx * vx + vy * vy, 1e-9)
            t = np.clip(((px - s[:, 0]) * vx + (py - s[:, 1]) * vy) / L2, 0, 1)
            d = np.hypot(px - (s[:, 0] + t * vx), py - (s[:, 1] + t * vy))
            k = int(d.argmin())
            if d[k] < bd:
                bd, best = float(d[k]), math.degrees(math.atan2(vx[k], vy[k])) % 180.0
        return best


class TerrainData:
    """Heights (vio_wrp.Terrain), obstacles, roads and land components of one terrain."""

    def __init__(self, tcfg, verbose=False):
        t0 = time.time()
        self.cfg = tcfg
        self.pbo = os.path.join(WORKSHOP, tcfg["wrp_pbo"])
        w = read_wrp(self.pbo)
        segs = []
        for _path, pts in w["road_parts"]:
            for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
                segs.append((x1, y1, x2, y2))
        self.T = WRP.Terrain(w["elev"], w["size"], np.array(segs).reshape(-1, 4), source=w["source"])
        self.size = float(w["size"])
        self.roads = SegmentGrid(self.T.segs)
        kinds = [classify_model(m) for m in w["models"]]
        objs = w["objects"]
        mi = objs["m"]
        scale = np.clip(np.linalg.norm(mi[:, 0:3], axis=1), 0.5, 3.0)
        kind = np.array([kinds[i][0] or "" for i in objs["mi"]])
        rad = np.array([kinds[i][1] for i in objs["mi"]]) * scale
        x, y = mi[:, 9].astype(float), mi[:, 11].astype(float)
        self.obj_kind, self.obj_x, self.obj_y, self.obj_r = kind, x, y, rad
        self.obj_model = np.array([w["models"][i] for i in objs["mi"]])
        hard = np.isin(kind, ["building", "wall", "rock", "pavement", "pond", "small"])
        self.hard = PointGrid(x[hard], y[hard], rad[hard])
        self.big = PointGrid(x[kind == "building"], y[kind == "building"], rad[kind == "building"])
        self.trees = PointGrid(x[kind == "tree"], y[kind == "tree"], rad[kind == "tree"])
        self.bushes = PointGrid(x[kind == "bush"], y[kind == "bush"], rad[kind == "bush"])
        self.n_objects = len(objs)
        self.version = w["version"]
        self._label_land()
        self.load_s = time.time() - t0
        if verbose:
            c = Counter(kind)
            say(f"{self.T.source}: OPRW v{self.version}, mapa {self.size:.0f} m, grilla {self.T.tx} (g={self.T.g:.2f} m), "
                f"{self.n_objects} objetos ({', '.join(f'{k or 'ignorados'} {v}' for k, v in c.most_common())}), "
                f"{len(self.T.segs)} tramos de camino, {self.load_s:.1f} s")

    def _label_land(self):
        """4-connected land components on the height grid (h > 0)."""
        land = self.T.e > 0.0
        lab = np.zeros(land.shape, dtype=np.int32)
        try:
            from scipy import ndimage
            lab, n = ndimage.label(land)
        except ImportError:  # pure-Python fallback
            n = 0
            ty, tx = land.shape
            for j0 in range(ty):
                for i0 in range(tx):
                    if land[j0, i0] and not lab[j0, i0]:
                        n += 1
                        lab[j0, i0] = n
                        q = deque([(j0, i0)])
                        while q:
                            j, i = q.popleft()
                            for jj, ii in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
                                if 0 <= jj < ty and 0 <= ii < tx and land[jj, ii] and not lab[jj, ii]:
                                    lab[jj, ii] = n
                                    q.append((jj, ii))
        self.labels = lab
        self.n_components = int(lab.max())
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        self.main_component = int(sizes.argmax())
        self.component_km2 = {int(k): float(v) * self.T.g ** 2 / 1e6 for k, v in enumerate(sizes) if k and v}

    def component(self, x, y):
        i = int(round(min(max(x / self.T.g, 0), self.T.tx - 1)))
        j = int(round(min(max(y / self.T.g, 0), self.T.ty - 1)))
        return int(self.labels[j, i])

    def h(self, x, y):
        return float(self.T.h(x, y))

    def slope(self, x, y, r=10.0):
        return float(self.T.slope(x, y, r))

    def slope_stats(self, x, y, radius, step=10.0):
        return self.T.slope_stats(x, y, radius, step)

    def wet(self, x, y, radius, step=10.0, level=0.3):
        return self.T.wet_share(x, y, radius, step, level)

    def min_h(self, x, y, half):
        return self.T.min_h(x, y, half)

    def road(self, x, y, cap=300.0):
        return self.roads.dist(x, y, cap)

    def clear(self, x, y):
        """(hard clearance, tree clearance, bush clearance), each capped at 40 m."""
        return self.hard.clearance(x, y), self.trees.clearance(x, y), self.bushes.clearance(x, y)

    def buildings_near(self, x, y, R):
        return self.big.count(x, y, R)

    def trees_near(self, x, y, R):
        return self.trees.count(x, y, R)


def load_terrains():
    with open(TERRAINS_JSON, encoding="utf-8") as f:
        return json.load(f)


def terrain_cfg(key):
    data = load_terrains()
    k = key.lower()
    if k not in data["terrains"]:
        sys.exit(f"ERROR: terreno desconocido '{key}' (hay: {', '.join(data['terrains'])})")
    t = dict(data["terrains"][k])
    t["id"] = k
    return t


def terrain_for_world(world):
    """Terrain key whose worldName matches (case-insensitive), or None."""
    if not os.path.exists(TERRAINS_JSON):
        return None
    for k, t in load_terrains()["terrains"].items():
        if t["world"].lower() == world.lower():
            return k
    return None


def read_cfg_worlds(tcfg):
    """CfgWorlds facts from the terrain's rapified config.bin: world class, description, Names (towns)."""
    path = os.path.join(WORKSHOP, tcfg["config_pbo"])
    p = Pbo(path)
    e = next(e for e in p.entries if e["name"].lower() == "config.bin")
    rap = Rap(p.content(e))
    root = rap.tree(rap.root)
    worlds = root.get("cfgworlds", {})
    out = {}
    for wname, w in worlds.items():
        if not isinstance(w, dict) or "names" not in w:
            continue
        names = []
        for cname, n in w["names"].items():
            if isinstance(n, dict) and "position" in n:
                names.append(dict(cls=n["_name"], name=n.get("name", ""), type=n.get("type", ""),
                                  pos=[float(v) for v in n["position"][:2]]))
        out = dict(world=w["_name"], description=w.get("description", ""), names=names,
                   ils=w.get("ilsposition"), mapsize=w.get("mapsize"))
    return out


class Rap:
    """Minimal rapified config reader (same format as work/vio_gear/scan/cfgscan.py)."""

    def __init__(self, b):
        if b[:4] != b"\0raP":
            raise ValueError("config.bin no está rapificado")
        self.b = b
        self.root = 16

    def _s(self, p):
        e = self.b.index(b"\0", p)
        return self.b[p:e].decode("utf-8", "replace"), e + 1

    def _cint(self, p):
        v = sh = 0
        while True:
            c = self.b[p]
            p += 1
            v |= (c & 0x7F) << sh
            sh += 7
            if not c & 0x80:
                return v, p

    def _arr(self, p):
        n, p = self._cint(p)
        out = []
        for _ in range(n):
            t = self.b[p]
            p += 1
            if t in (0, 4):
                s, p = self._s(p)
                out.append(s)
            elif t == 1:
                out.append(struct.unpack_from("<f", self.b, p)[0])
                p += 4
            elif t == 2:
                out.append(struct.unpack_from("<i", self.b, p)[0])
                p += 4
            elif t == 3:
                a, p = self._arr(p)
                out.append(a)
            elif t == 6:
                out.append(struct.unpack_from("<q", self.b, p)[0])
                p += 8
            else:
                raise ValueError(f"tipo de elemento {t}")
        return out, p

    def tree(self, p, name=""):
        _inh, p = self._s(p)
        n, p = self._cint(p)
        node = {"_name": name}
        for _ in range(n):
            t = self.b[p]
            p += 1
            if t == 0:
                nm, p = self._s(p)
                off = struct.unpack_from("<I", self.b, p)[0]
                p += 4
                node[nm.lower()] = self.tree(off, nm)
            elif t == 1:
                st = self.b[p]
                p += 1
                nm, p = self._s(p)
                if st == 1:
                    v = struct.unpack_from("<f", self.b, p)[0]
                    p += 4
                elif st == 2:
                    v = struct.unpack_from("<i", self.b, p)[0]
                    p += 4
                elif st == 6:
                    v = struct.unpack_from("<q", self.b, p)[0]
                    p += 8
                else:
                    v, p = self._s(p)
                node[nm.lower()] = v
            elif t == 2:
                nm, p = self._s(p)
                v, p = self._arr(p)
                node[nm.lower()] = v
            elif t in (3, 4):
                _nm, p = self._s(p)
            elif t == 5:
                p += 4
                nm, p = self._s(p)
                v, p = self._arr(p)
                node[nm.lower()] = v
            else:
                raise ValueError(f"tipo de entrada {t}")
        return node


# =====================================================================================================
# 2) SMALL GEOMETRY HELPERS
# =====================================================================================================

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def bearing(frm, to):
    """Arma direction (degrees clockwise from north) from `frm` to `to`."""
    return math.degrees(math.atan2(to[0] - frm[0], to[1] - frm[1])) % 360.0


def polar(c, r, deg):
    a = math.radians(deg)
    return (c[0] + r * math.sin(a), c[1] + r * math.cos(a))


def ang_diff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


# =====================================================================================================
# 3) GENERATOR
# =====================================================================================================

class Rules:
    """Placement thresholds (final_plan steps 3-7, plus object clearances that the design could not check)."""
    depot_ring_max = 300.0
    depot_slope = 0.10
    depot_hard, depot_tree, depot_bush, depot_road = 8.0, 6.0, 2.5, 10.0
    depot_spacing, depot_spacing_hard = 600.0, 550.0
    camp_r = (120.0, 280.0)
    camp_slope, camp_hard, camp_tree, camp_bush, camp_road, camp_gap = 0.15, 6.0, 4.0, 1.5, 8.0, 150.0
    def_slope, def_hard, def_tree, def_road, def_gap = 0.20, 3.0, 2.0, 6.0, 12.0
    sp_r = (60.0, 250.0)
    sp_slope, sp_hard, sp_tree, sp_road, sp_gap = 0.25, 4.0, 1.5, 5.0, 40.0
    # Base core (60 m): p90 < 10 %, max < 15 %; whole base area (100 m): p90 < 12 % (warning above 8 %).
    # The review's 100 m / 8 % rule leaves no start at all on Everon's hilly south-east (documented deviation).
    start_p90, start_max, start_r, start_p90_outer, start_r_outer = 0.10, 0.15, 60.0, 0.12, 100.0
    start_dry_h, start_wet_r, start_depot, start_edge = 2.0, 80.0, 600.0, 400.0
    start_hard, start_trees_r, start_trees_max = 30.0, 60.0, 25
    hold_slope_r, hold_slope, hold_dry_h, hold_depot, hold_depot_min, hold_start = 20.0, 0.05, 2.0, 1500.0, 800.0, 1000.0
    hold_hard, hold_tree = 25.0, 12.0
    counts = {"L": dict(camps=3, defenses=5, at=1, spawns=8), "M": dict(camps=2, defenses=4, at=1, spawns=6),
              "S": dict(camps=1, defenses=3, at=1, spawns=5)}


def _dry(td, x, y, half, level):
    return td.min_h(x, y, half) >= level


def find_depot(td, town, placed, dry_h, rules=Rules):
    """Best depot spot within 300 m of the label (rings of 12.5 m, 32 bearings). Returns (x, y, info) or None."""
    lx, ly = town["label"]
    if town.get("depot"):
        x, y = town["depot"]
        return x, y, dict(pinned=True, r=dist((x, y), (lx, ly)))
    main = td.main_component
    best = None
    for spacing in (rules.depot_spacing, rules.depot_spacing_hard):
        for ri in range(0, int(rules.depot_ring_max / 12.5) + 1):
            r = ri * 12.5
            for k in range(1 if r == 0 else 32):
                x, y = polar((lx, ly), r, k * 11.25 + (ri % 2) * 5.625)
                if not (50 <= x <= td.size - 50 and 50 <= y <= td.size - 50):
                    continue
                if td.component(x, y) != main or not _dry(td, x, y, 6.0, dry_h):
                    continue
                if any(dist((x, y), p) < spacing for p in placed):
                    continue
                s = td.slope(x, y)
                if s >= rules.depot_slope:
                    continue
                hard, tree, bush = td.clear(x, y)
                if hard < rules.depot_hard or tree < rules.depot_tree or bush < rules.depot_bush:
                    continue
                rd = td.road(x, y)
                if rd < rules.depot_road:
                    continue
                if td.wet(x, y, 40.0) > 0:
                    continue
                p90, _mx = td.slope_stats(x, y, 15.0, 5.0)
                if p90 >= 0.12:
                    continue
                nb = td.buildings_near(x, y, 120.0)
                score = (max(0.0, 50 - r, r - 150) / 50.0 + (max(0.0, 15 - rd) / 5.0 + max(0.0, rd - 60) / 40.0)
                         + s * 10 - min(hard, 20.0) / 40.0 - min(nb, 8) / 16.0)
                if best is None or score < best[0]:
                    best = (score, x, y, dict(r=r, slope=s, road=rd, hard=hard, tree=tree, bld120=nb, spacing=spacing))
        if best:
            break
    if best is None:
        return None
    return best[1], best[2], best[3]


def place_children(td, town, others, dry_h, rng, rules=Rules):
    """Camps, defenses and spawn points of one town (all synced to it). `others` = depots of the other towns."""
    dx, dy = town["pos"]
    tier = town["tier"]
    cnt = dict(rules.counts[tier])
    for k in ("camps", "defenses", "spawns"):
        if k in town:
            cnt[k] = int(town[k])
    rng_lim = (town.get("range") or 550) - 50
    main = td.main_component
    notes = []

    def own(x, y, margin):
        d0 = dist((x, y), (dx, dy))
        return all(dist((x, y), o) - d0 >= margin for o in others)

    taken = []  # (x, y, min gap) of everything placed for this town (depot footprint first)
    taken.append((dx, dy, 15.0))

    def free(x, y, gap):
        return all(dist((x, y), (tx, ty)) >= max(gap, tg) for tx, ty, tg in taken)

    # --- camps
    camps = []
    base = float(rng.uniform(0, 360))
    for k in range(cnt["camps"]):
        target = base + k * 360.0 / cnt["camps"]
        best = None
        for spread in (25.0, 60.0, 120.0):
            for r in np.arange(rules.camp_r[0], min(rules.camp_r[1], rng_lim) + 0.1, 10.0):
                for db in np.arange(-spread, spread + 0.1, 5.0):
                    x, y = polar((dx, dy), r, target + db)
                    if td.component(x, y) != main or not _dry(td, x, y, 3.0, dry_h) or not own(x, y, 80.0):
                        continue
                    if any(dist((x, y), c) < rules.camp_gap for c in camps + town.get("_foreign_camps", [])):
                        continue
                    if not free(x, y, 30.0):
                        continue
                    s = td.slope(x, y, 10.0)
                    if s >= rules.camp_slope:
                        continue
                    hard, tree, bush = td.clear(x, y)
                    if hard < rules.camp_hard or tree < rules.camp_tree or bush < rules.camp_bush:
                        continue
                    if td.road(x, y) < rules.camp_road or td.wet(x, y, 20.0) > 0:
                        continue
                    nb = td.buildings_near(x, y, 80.0)
                    score = abs(r - 180) / 100.0 + s * 5 + abs(db) / 50.0 - min(nb, 5) / 10.0
                    if best is None or score < best[0]:
                        best = (score, x, y)
            if best:
                break
        if best:
            camps.append((best[1], best[2]))
            taken.append((best[1], best[2], 12.0))
        else:
            notes.append(f"campamento {k + 1}: sin sitio libre")
    # --- defenses: one MG near the depot, one next to each camp, the rest on the road approaches (AT first)
    n_def = cnt["defenses"]
    n_at = min(cnt.get("at", 1), n_def)
    defenses = []

    def best_spot(center, r0, r1, prefer_dir=None, near_road=False):
        best = None
        for r in np.arange(r0, r1 + 0.1, 2.5 if r1 <= 40 else 5.0):
            for b in range(0, 360, 10):
                x, y = polar(center, r, b)
                if dist((x, y), (dx, dy)) > rng_lim or td.component(x, y) != main or not _dry(td, x, y, 1.5, dry_h):
                    continue
                if not free(x, y, rules.def_gap):
                    continue
                s = td.slope(x, y, 3.0)
                if s >= rules.def_slope:
                    continue
                hard, tree, _bush = td.clear(x, y)
                if hard < rules.def_hard or tree < rules.def_tree:
                    continue
                rd = td.road(x, y)
                if rd < rules.def_road:
                    continue
                out = bearing((dx, dy), (x, y))
                score = s * 5 - min(hard, 10.0) / 20.0
                if prefer_dir is not None:
                    score += ang_diff(out, prefer_dir) / 90.0
                if near_road:
                    score += max(0.0, rd - 25.0) / 15.0
                if best is None or score < best[0]:
                    best = (score, x, y)
        return best

    slots = [("depot", (dx, dy), 15.0, 30.0, None, False)]
    for c in camps:
        slots.append(("camp", c, 15.0, 30.0, bearing((dx, dy), c), False))
    # road approaches: directions where a road leaves the town (sampled at 120 m)
    road_dirs = []
    for b in range(0, 360, 15):
        p = polar((dx, dy), 120.0, b)
        if td.road(*p) < 20:
            road_dirs.append(b)
    outer_dirs = []
    for b in road_dirs:
        if all(ang_diff(b, o) >= 50 for o in outer_dirs):
            outer_dirs.append(b)
    if not outer_dirs:
        outer_dirs = [base + 180.0]
    i = 0
    while len(slots) < n_def:
        slots.append(("outer", (dx, dy), 60.0, 160.0, outer_dirs[i % len(outer_dirs)] + 20.0 * (i // len(outer_dirs)), True))
        i += 1
    slots = slots[:n_def]
    # AT goes to the outer road slots first, then to camps from the last one backwards
    kinds = ["MG"] * len(slots)
    order = [k for k, s in enumerate(slots) if s[0] == "outer"] + [k for k, s in reversed(list(enumerate(slots))) if s[0] == "camp"]
    for k in order[:n_at]:
        kinds[k] = "AT"
    for (what, center, r0, r1, pdir, nroad), kind in zip(slots, kinds):
        b = best_spot(center, r0, r1, pdir, nroad)
        if b is None and what != "depot":
            b = best_spot((dx, dy), 40.0, min(250.0, rng_lim), pdir, False)
        if b is None:
            notes.append(f"defensa {kind} ({what}): sin sitio libre")
            continue
        x, y = b[1], b[2]
        defenses.append((x, y, bearing((dx, dy), (x, y)) if dist((x, y), (dx, dy)) > 1 else 0.0, kind))
        taken.append((x, y, rules.def_gap))
    # --- spawn points: spread around the depot, 60-250 m out, on clear dry land
    cands = []
    for r in np.arange(rules.sp_r[0], min(rules.sp_r[1], rng_lim) + 0.1, 10.0):
        for b in range(0, 360, 10):
            x, y = polar((dx, dy), r, b + (r % 20))
            if td.component(x, y) != main or not _dry(td, x, y, 2.0, max(1.0, dry_h - 0.5)) or not own(x, y, 40.0):
                continue
            if not free(x, y, 25.0):
                continue
            if td.slope(x, y, 3.0) >= rules.sp_slope:
                continue
            hard, tree, _bush = td.clear(x, y)
            if hard < rules.sp_hard or tree < rules.sp_tree or td.road(x, y) < rules.sp_road or td.wet(x, y, 15.0) > 0:
                continue
            cands.append((x, y, td.buildings_near(x, y, 60.0)))
    spawns = []
    while cands and len(spawns) < cnt["spawns"]:
        def gain(c):
            if not spawns:
                return -abs(dist(c[:2], (dx, dy)) - 120) / 100.0 + min(c[2], 4) / 4.0
            return min(dist(c[:2], s) for s in spawns) / 100.0 + min(c[2], 4) / 8.0
        c = max(cands, key=gain)
        if spawns and min(dist(c[:2], s) for s in spawns) < rules.sp_gap:
            break
        spawns.append((c[0], c[1]))
        cands = [k for k in cands if dist(k[:2], (c[0], c[1])) >= rules.sp_gap]
    if len(spawns) < cnt["spawns"]:
        notes.append(f"puntos de aparición: {len(spawns)} de {cnt['spawns']}")
    return camps, defenses, spawns, notes


def start_ok(td, x, y, depots, rules=Rules, strict=True):
    """(ok, info) for a base start marker (final_plan step 5)."""
    info = {}
    if not (rules.start_edge <= x <= td.size - rules.start_edge and rules.start_edge <= y <= td.size - rules.start_edge):
        return False, {"why": "borde"}
    if td.component(x, y) != td.main_component:
        return False, {"why": "isla"}
    if td.h(x, y) < rules.start_dry_h or td.wet(x, y, rules.start_wet_r, 20.0) > 0:
        return False, {"why": "agua"}
    p90, mx = td.slope_stats(x, y, rules.start_r, 10.0)
    p90o, mxo = td.slope_stats(x, y, rules.start_r_outer, 10.0)
    info.update(p90=p90, max=mx, p90_100=p90o, max_100=mxo)
    if strict and (p90 >= rules.start_p90 or mx >= rules.start_max or p90o >= rules.start_p90_outer):
        return False, dict(info, why="pendiente")
    dd = min(dist((x, y), d) for d in depots)
    info["depot"] = dd
    if dd < rules.start_depot:
        return False, dict(info, why="depósito cerca")
    hard = td.big.clearance(x, y, 60.0)
    info["bld"] = hard
    if hard < rules.start_hard:
        return False, dict(info, why="edificios")
    nt = td.trees_near(x, y, rules.start_trees_r)
    info["trees60"] = nt
    if strict and nt > rules.start_trees_max:
        return False, dict(info, why="árboles")
    info["road"] = td.road(x, y)
    return True, info


def snap_start(td, target, depots, radius=120.0, rules=Rules):
    """Spot nearest to the curated `target` (within radius, 20 m rings) that passes start_ok; prefers flat, open ground."""
    best = None
    for r in np.arange(0, radius + 0.1, 20.0):
        n = 1 if r == 0 else max(8, int(2 * math.pi * r / 20))
        for k in range(n):
            x, y = polar(target, r, k * 360.0 / n)
            ok, info = start_ok(td, x, y, depots, rules)
            if not ok:
                continue
            score = r / 40.0 + info["p90"] * 20 + info["trees60"] / 20.0 + max(0.0, info["road"] - 150) / 200.0
            if best is None or score < best[0]:
                best = (score, x, y, info)
    return best


def holding_ok(td, x, y, depots, starts, rules=Rules):
    if not (100 <= x <= td.size - 100 and 100 <= y <= td.size - 100):
        return False, {}
    if td.min_h(x, y, 20.0) < rules.hold_dry_h:
        return False, {}
    _p90, mx = td.slope_stats(x, y, rules.hold_slope_r, 5.0)
    if mx >= rules.hold_slope:
        return False, {}
    hard, tree, _b = td.clear(x, y)
    if hard < rules.hold_hard or tree < rules.hold_tree:
        return False, {}
    dd = min(dist((x, y), d) for d in depots)
    ds = min(dist((x, y), s) for s in starts) if starts else 1e9
    if dd < rules.hold_depot_min or ds < rules.hold_start:
        return False, {}
    return True, dict(depot=dd, start=ds, slope=mx, island=td.component(x, y) != td.main_component)


def find_holding(td, hint, depots, starts, used, radius=1500.0, rules=Rules):
    """Holding area (CTI_*Respawn, Prison) nearest to the hint: islands first, then >= 1500 m from depots."""
    best = None
    step = 25.0
    for r in np.arange(0, radius + 0.1, step):
        n = 1 if r == 0 else max(8, int(2 * math.pi * r / step))
        for k in range(n):
            x, y = polar(hint, r, k * 360.0 / n)
            ok, info = holding_ok(td, x, y, depots, starts, rules)
            if not ok or any(dist((x, y), u) < 300 for u in used):
                continue
            score = r / 500.0 + (0 if info["depot"] >= rules.hold_depot else 5) + (0 if info["island"] else 0.5)
            if best is None or score < best[0]:
                best = (score, x, y, info)
        if best and r > 300:
            break
    return best


def removal_templates(towns, anchors):
    """Towns_Removed{XSmall,Small,Medium,Large}: remove by ascending importance, never an anchor (review fix 5)."""
    n = len(towns)
    rank = {"L": 3, "M": 2, "S": 1}
    order = sorted([t for t in towns if t["name"] not in anchors],
                   key=lambda t: (rank[t["tier"]], t.get("_bld", 0), -t["_index"]))
    out = {}
    for tpl, share in (("XSmall", 0.30), ("Small", 0.37), ("Medium", 0.65), ("Large", 0.90)):
        keep = max(int(round(share * n)), len(anchors))
        n_remove = max(0, min(len(order), n - keep))
        out[tpl] = [t["name"] for t in order[:n_remove]]
    return out


def farthest_starts(td, depots, k, rules=Rules, step=250.0):
    """CW-style alternative: K generic markers by farthest-point sampling on a 250 m grid (final_plan, --generic-starts)."""
    cands = []
    for x in np.arange(rules.start_edge, td.size - rules.start_edge + 1, step):
        for y in np.arange(rules.start_edge, td.size - rules.start_edge + 1, step):
            ok, _info = start_ok(td, x, y, depots, rules)
            if ok and 700 <= min(dist((x, y), d) for d in depots) <= 1800:
                cands.append((float(x), float(y)))
    if len(cands) < 2:
        return []
    # farthest pair first
    a = np.array(cands)
    d = np.hypot(a[:, None, 0] - a[None, :, 0], a[:, None, 1] - a[None, :, 1])
    i, j = np.unravel_index(int(d.argmax()), d.shape)
    chosen = [cands[i], cands[j]]
    while len(chosen) < k:
        m = np.min([np.hypot(a[:, 0] - c[0], a[:, 1] - c[1]) for c in chosen], axis=0)
        n = int(m.argmax())
        if m[n] < 1000:
            break
        chosen.append(cands[n])
    return chosen


def generate(tcfg, td, generic_starts=0):
    """Full generation plan (no files): towns with children, starts, holding areas, templates."""
    dry_h = float(tcfg.get("min_dry_h", 1.5))
    seed = int(tcfg.get("seed", 1))
    towns = []
    for i, t in enumerate(tcfg["towns"]):
        t = dict(t)
        t["_index"] = i
        t["_bld"] = td.buildings_near(t["label"][0], t["label"][1], 250.0)
        towns.append(t)
    names = [t["name"] for t in towns]
    dup = [n for n, c in Counter(names).items() if c > 1]
    if dup:
        raise ValueError(f"nombres de pueblo repetidos: {dup}")
    for t in towns:
        if '"' in t["name"] or not t["name"].strip() or "$STR" in t["name"] or not t["name"].isascii():
            raise ValueError(f"nombre de pueblo inválido: {t['name']!r}")
    # depots: big towns first so they get the best spots and the spacing is enforced on the small ones
    rank = {"L": 0, "M": 1, "S": 2}
    placed = []
    for t in sorted(towns, key=lambda t: (rank[t["tier"]], t["_index"])):
        res = find_depot(td, t, placed, dry_h)
        if res is None:
            raise ValueError(f"{t['name']}: no hay sitio para el depósito a menos de 300 m de la etiqueta")
        t["pos"] = (res[0], res[1])
        t["depot_info"] = res[2]
        t["yaw"] = bearing(t["pos"], t["label"]) if dist(t["pos"], t["label"]) > 5 else 0.0
        placed.append(t["pos"])
    # range only for tight neighbours (review fix 8)
    for t in towns:
        nn = min(dist(t["pos"], o["pos"]) for o in towns if o is not t)
        t["nn"] = nn
        if "range" not in t and nn < 850:
            t["range"] = int(min(550, max(350, round(0.65 * nn))))
    # children
    all_camps = []
    for t in sorted(towns, key=lambda t: (rank[t["tier"]], t["_index"])):
        rng = np.random.default_rng(seed * 1000 + t["_index"])
        t["_foreign_camps"] = all_camps
        others = [o["pos"] for o in towns if o is not t]
        t["camps"], t["defenses"], t["spawns"], t["notes"] = place_children(td, t, others, dry_h, rng)
        all_camps = all_camps + t["camps"]
        del t["_foreign_camps"]
    depots = [t["pos"] for t in towns]
    # starts
    west, east, start_notes = [], [], []
    if generic_starts:
        generic = farthest_starts(td, depots, generic_starts)
        start_notes.append(f"modo genérico: {len(generic)} marcadores cti-spawnN por muestreo de punto más lejano")
    else:
        generic = None
        for side, lst in (("west", west), ("east", east)):
            for k, target in enumerate(tcfg[f"base_starts_{side}"]):
                b = snap_start(td, tuple(target), depots)
                if b is None:
                    raise ValueError(f"inicio {side}{k} cerca de {target}: no hay sitio que cumpla las reglas a menos de 120 m")
                lst.append(dict(pos=(b[1], b[2]), target=tuple(target), info=b[3]))
    # anchors (review fix 5): one start per side within 950 m of an anchor, every start within 1900 m of a town,
    # so the side lists survive "Start Near towns" 1-2 KM with every town template
    anchors = {"west": list(tcfg.get("anchors_west", [])), "east": list(tcfg.get("anchors_east", []))}
    pos_of = {t["name"]: t["pos"] for t in towns}
    for side in anchors:
        for a in anchors[side]:
            if a not in names:
                raise ValueError(f"ancla desconocida: {a}")
        lst = west if side == "west" else east
        if lst:
            if not anchors[side]:
                raise ValueError(f"faltan anclas del bando {side}")
            if min(dist(s["pos"], pos_of[a]) for s in lst for a in anchors[side]) > 950:
                raise ValueError(f"ningún inicio del bando {side} está a menos de 950 m de un pueblo ancla")
            far = [s["pos"] for s in lst if min(dist(s["pos"], p) for p in pos_of.values()) > 1900]
            if far:
                raise ValueError(f"inicios del bando {side} a más de 1900 m de todo pueblo: {far}")
    # holding areas
    starts_xy = [s["pos"] for s in west + east] if generic is None else list(generic)
    hold = {}
    used = []
    hints = tcfg.get("holding", {})
    for key, marker in (("west", "CTI_WestRespawn"), ("east", "CTI_EastRespawn"), ("prison", "Prison")):
        hint = hints.get(key)
        if hint is None:
            raise ValueError(f"falta holding.{key} en el JSON del terreno")
        b = find_holding(td, tuple(hint), depots, starts_xy, used)
        if b is None:
            raise ValueError(f"{marker}: no hay sitio plano y lejos de los pueblos cerca de {hint}")
        hold[marker] = dict(pos=(b[1], b[2]), info=b[3])
        used.append((b[1], b[2]))
    keep = set(tcfg.get("keep_always", []))
    for a in keep:
        if a not in names:
            raise ValueError(f"keep_always desconocido: {a}")
    templates = removal_templates(towns, set(anchors["west"]) | set(anchors["east"]) | keep)
    return dict(towns=towns, west=west, east=east, generic=generic, anchors=anchors, holding=hold,
                templates=templates, start_notes=start_notes, terrain=tcfg)


# =====================================================================================================
# 4) MISSION.SQM REBUILD (template = pristine CW Malden; only map-specific content is replaced)
# =====================================================================================================

DELETE_TYPES = {"LocationArea_F", "LocationCamp_F", "LocationRespawnPoint_F", "ModuleHideTerrainObjects_F"}
HOLDING_MARKERS = ("CTI_WestRespawn", "CTI_EastRespawn", "Prison")


def template_pbo():
    """The pristine CW Malden PBO, after checking it is the expected one."""
    hits = glob.glob(os.path.join(WORKSHOP, TEMPLATE_WS, "*_legacy.bin"))
    if len(hits) != 1:
        sys.exit(f"ERROR: no encuentro la misión plantilla CW Malden (Workshop {TEMPLATE_WS})")
    p = Pbo(hits[0])
    if not p.sha1_ok or len(p.entries) != TEMPLATE_ENTRIES or any(Pbo.is_compressed(e) for e in p.entries):
        sys.exit(f"ERROR: {hits[0]} no es la plantilla esperada (SHA1, {TEMPLATE_ENTRIES} entradas, sin comprimir)")
    sqm = p.content(p.find("mission.sqm"))
    if hashlib.sha1(sqm).hexdigest() != TEMPLATE_SQM_SHA1:
        sys.exit("ERROR: el mission.sqm de la plantilla cambió (¿actualización del Workshop?); revisar antes de generar")
    return p


def _items(ents):
    """Entity classes of an Entities/Links block (in Eden every class there is an ItemK; new ones start as ItemX)."""
    return [c for c in ents.items if isinstance(c, SQM.Cls)]


def _renumber(ents):
    """Children Item0..Item{n-1} in order, items=n (marks the block for rewriting)."""
    kids = _items(ents)
    for k, c in enumerate(kids):
        if c.name != f"Item{k}":
            c.name = f"Item{k}"
            c.dirty = True
    ents.items = [a for a in ents.items if not isinstance(a, SQM.Cls)]
    ents.items = [a for a in ents.items if not (isinstance(a, SQM.Asg) and a.key == "items")]
    ents.items = [SQM.Asg("items", len(kids))] + ents.items + kids
    ents.dirty = True


def _pos(item):
    """(x, y, z) of an entity (Markers keep position[] at item level)."""
    pi = item.cls("PositionInfo")
    p = (pi.get("position") if pi is not None else None) or item.get("position")
    return (float(p[0]), float(p[2]), float(p[1])) if p else None


def _fmt_f(v, nd=3):
    return float(round(v, nd))


def _new_marker(name, x, y, z, ident, color=None):
    items = [SQM.Asg("dataType", "Marker"), SQM.Asg("position", [_fmt_f(x), _fmt_f(z, 4), _fmt_f(y)], arr=True),
             SQM.Asg("name", name), SQM.Asg("type", "Empty")]
    if color == "respawn":
        items += [SQM.Asg("colorName", "ColorRed"), SQM.Asg("fillName", "Border"), SQM.Asg("drawBorder", 1)]
    elif color == "prison":
        items += [SQM.Asg("colorName", "ColorPink")]
    items.append(SQM.Asg("id", ident))
    return SQM.Cls("ItemX", items)


def _new_logic(x, y, z, yaw_deg, ident, ltype, name=None, init=None):
    pinfo = [SQM.Asg("position", [_fmt_f(x), _fmt_f(z, 4), _fmt_f(y)], arr=True)]
    yaw = math.radians(yaw_deg % 360.0)
    if abs(yaw) > 1e-6:
        pinfo.append(SQM.Asg("angles", [0, float(round(yaw, 7)), 0], arr=True))
    items = [SQM.Asg("dataType", "Logic"), SQM.Cls("PositionInfo", pinfo)]
    if name is not None:
        items.append(SQM.Asg("name", name))
    if init is not None:
        items.append(SQM.Asg("init", init))
    items += [SQM.Asg("id", ident), SQM.Asg("type", ltype)]
    return SQM.Cls("ItemX", items)


def _new_layer(name, children, ident):
    ents = SQM.Cls("Entities", [])
    ents.items = list(children)
    _renumber(ents)
    return SQM.Cls("ItemX", [SQM.Asg("dataType", "Layer"), SQM.Asg("name", name), ents, SQM.Asg("id", ident)])


def town_init(name, side, start_sv, max_sv, value, rng=None):
    args = f'[this, "{name}", {side}, {start_sv}, {max_sv}, {value}' + (f", {rng}" if rng else "") + "]"
    return "call{nullReturn = " + args + ' execVM "Common\\Init\\Init_Location.sqf"}'


def logic_init(total, templates):
    sqf_list = lambda names: "[" + ",".join(f'"{n}"' for n in names) + "]"
    parts = [f'this setVariable ["totalTowns",{total}];']
    for tpl in ("XSmall", "Small", "Medium", "Large"):
        parts.append(f'this setVariable ["Towns_Removed{tpl}",{sqf_list(templates[tpl])}];')
    parts.append('nullReturn = [this] ExecVM "Common\\Init\\Init_LocationMode.sqf";')
    return "call{" + " ".join(parts) + "}"


def start_markers(plan):
    """[(marker name, (x, y))]: cti-spawn0/1 = West/East primary (fallback pair, Init_Server.sqf:123-124, 137-140),
    then the families cti-spawn-westN / cti-spawn-eastN with every West/East start (review fix 4)."""
    if plan.get("generic"):
        return [(f"cti-spawn{k}", p) for k, p in enumerate(plan["generic"])]
    out = [("cti-spawn0", plan["west"][0]["pos"]), ("cti-spawn1", plan["east"][0]["pos"])]
    out += [(f"cti-spawn-west{k}", s["pos"]) for k, s in enumerate(plan["west"])]
    out += [(f"cti-spawn-east{k}", s["pos"]) for k, s in enumerate(plan["east"])]
    return out


def rebuild_sqm(text, plan, td):
    """New mission.sqm text from the template text and a generation plan."""
    root = SQM.parse(text)
    edit = root.cls("EditorData")
    mission = root.cls("Mission")
    ents = mission.cls("Entities")
    idp = edit.cls("ItemIDProvider")
    next_id = first_id = int(idp.get("nextID"))

    # --- old holding markers (units are translated with them)
    old_hold = {}

    def scan(e):
        for it in _items(e):
            if it.get("dataType") == "Marker" and it.get("name") in HOLDING_MARKERS:
                old_hold[it.get("name")] = _pos(it)
            if it.get("dataType") == "Layer":
                scan(it.cls("Entities"))
    scan(ents)
    for m in ("CTI_WestRespawn", "CTI_EastRespawn"):
        if m not in old_hold:
            raise ValueError(f"la plantilla no tiene {m}")

    # --- delete map-specific content (recursively), remember the slot of the old Towns layer
    deleted = set()

    def doomed(it):
        dt = it.get("dataType")
        if dt == "Logic":
            if it.get("type") in DELETE_TYPES:
                return True
            init = it.get("init") or ""
            return it.get("type") == "Logic" and any(k in init for k in ("cti_defense_kind", "cti_mortar", "cti_dock"))
        if dt == "Object":
            return it.get("side") == "Empty"
        if dt == "Marker":
            nm = it.get("name") or ""
            return bool(SPAWN_RE.match(nm)) or nm in HOLDING_MARKERS
        return False

    def purge(e, top=False):
        """Drop doomed entities (and layers left empty); returns the slot of the first removed top-level layer."""
        keep, slot = [], None
        for it in _items(e):
            if it.get("dataType") == "Layer":
                purge(it.cls("Entities"))
                if not _items(it.cls("Entities")):
                    deleted.add(int(it.get("id")))
                    if top and slot is None:
                        slot = len(keep)
                    continue
            if doomed(it):
                deleted.add(int(it.get("id")))
                continue
            keep.append(it)
        e.items = [a for a in e.items if not isinstance(a, SQM.Cls)] + keep
        _renumber(e)
        return slot
    towns_slot = purge(ents, top=True)
    if towns_slot is None:
        towns_slot = len(_items(ents))

    # --- find kept entities
    by_name = {}
    units = []  # (side, object Cls)

    def collect(e):
        for it in _items(e):
            dt = it.get("dataType")
            if dt == "Layer":
                collect(it.cls("Entities"))
            elif dt == "Group":
                side = it.get("side")
                for o in _items(it.cls("Entities")):
                    if o.get("dataType") == "Object":
                        units.append((side, o))
            elif it.get("name"):
                by_name[it.get("name")] = it
    collect(ents)
    for nm in ("CTI_WEST", "CTI_EAST", "CTI_Logic"):
        if nm not in by_name:
            raise ValueError(f"la plantilla no tiene {nm}")
    side_logic = {"West": by_name["CTI_WEST"], "East": by_name["CTI_EAST"]}
    sys_layer = None
    for it in _items(ents):
        if it.get("dataType") == "Layer" and any(c is by_name["CTI_Logic"] for c in _items(it.cls("Entities"))):
            sys_layer = it
    if sys_layer is None:
        raise ValueError("no encuentro la capa SYSTEM & LOGIC")

    # --- new holding markers and the translation of units / side logics
    new_hold = {k: v["pos"] for k, v in plan["holding"].items()}
    delta = {"West": (new_hold["CTI_WestRespawn"][0] - old_hold["CTI_WestRespawn"][0],
                      new_hold["CTI_WestRespawn"][1] - old_hold["CTI_WestRespawn"][1]),
             "East": (new_hold["CTI_EastRespawn"][0] - old_hold["CTI_EastRespawn"][0],
                      new_hold["CTI_EastRespawn"][1] - old_hold["CTI_EastRespawn"][1])}

    def move(it, side):
        pi = it.cls("PositionInfo")
        x, y, _z = _pos(it)
        nx, ny = x + delta[side][0], y + delta[side][1]
        pi.set("position", [_fmt_f(nx), _fmt_f(td.h(nx, ny), 4), _fmt_f(ny)], arr=True)
        ang = pi.get("angles")
        yaw = float(ang[1]) if ang else 0.0
        if abs(yaw) > 1e-6:
            pi.set("angles", [0, yaw, 0], arr=True)
        else:
            pi.remove("angles")
        it.remove("atlOffset")
        it.dirty = True
    for side, o in units:
        if side not in delta:
            raise ValueError(f"unidad jugable de bando {side} (solo se esperan West/East)")
        move(o, side)
    for side, lg in side_logic.items():
        move(lg, side)

    # --- CTI_Logic init
    by_name["CTI_Logic"].set("init", logic_init(len(plan["towns"]), plan["templates"]))

    # --- new markers in SYSTEM & LOGIC (before the kept logics)
    markers = []
    for name, (x, y) in start_markers(plan):
        markers.append(_new_marker(name, x, y, td.h(x, y), next_id))
        next_id += 1
    for name, color in (("CTI_EastRespawn", "respawn"), ("CTI_WestRespawn", "respawn"), ("Prison", "prison")):
        x, y = new_hold[name]
        markers.append(_new_marker(name, x, y, td.h(x, y), next_id, color))
        next_id += 1
    sents = sys_layer.cls("Entities")
    kept = _items(sents)
    sents.items = [a for a in sents.items if not isinstance(a, SQM.Cls)]
    sents.items += markers + kept
    _renumber(sents)
    sys_layer.dirty = True

    # --- towns layer: one sub-layer per town (town logic, camps, defenses, spawn points)
    links_child = []
    sub_layers = []
    n_layers = 1
    for k, t in enumerate(plan["towns"]):
        start_sv, max_sv, value = TIERS[t["tier"]]
        x, y = t["pos"]
        town_id = next_id
        children = [_new_logic(x, y, td.h(x, y), t["yaw"], town_id, "LocationArea_F", name=f"Town{k}",
                               init=town_init(t["name"], "resistance", start_sv, max_sv, value, t.get("range")))]
        next_id += 1
        for cx, cy in t["camps"]:
            children.append(_new_logic(cx, cy, td.h(cx, cy), bearing((x, y), (cx, cy)), next_id, "LocationCamp_F"))
            links_child.append((next_id, town_id))
            next_id += 1
        for dx, dy, yaw, kind in t["defenses"]:
            children.append(_new_logic(dx, dy, td.h(dx, dy), yaw, next_id, "Logic",
                                       init=f"call{{this setVariable ['cti_defense_kind', ['{kind}']];}}"))
            links_child.append((next_id, town_id))
            next_id += 1
        for sx, sy in t["spawns"]:
            children.append(_new_logic(sx, sy, td.h(sx, sy), 0.0, next_id, "LocationRespawnPoint_F"))
            links_child.append((next_id, town_id))
            next_id += 1
        sub_layers.append(_new_layer(t["name"], children, next_id))
        next_id += 1
        n_layers += 1
    towns_layer = _new_layer("Towns", sub_layers, next_id)
    next_id += 1
    kids = _items(ents)
    kids.insert(min(towns_slot, len(kids)), towns_layer)
    ents.items = [a for a in ents.items if not isinstance(a, SQM.Cls)] + kids
    _renumber(ents)

    # --- links: unit -> own side logic (looked up by name, review fix 9), then child -> town
    old_links = mission.cls("Connections")
    old_pairs = set()
    if old_links is not None:
        for l in _items(old_links.cls("Links")):
            old_pairs.add((int(l.get("item0")), int(l.get("item1"))))
    pairs = [(int(o.get("id")), int(side_logic[side].get("id"))) for side, o in units] + links_child
    unit_pairs = {(int(o.get("id")), int(side_logic[side].get("id"))) for side, o in units}
    if old_pairs and not unit_pairs <= old_pairs:
        raise ValueError("los enlaces unidad -> lógica de bando no coinciden con la plantilla")
    links = SQM.Cls("Links", [])
    for k, (a, b) in enumerate(pairs):
        links.items.append(SQM.Cls(f"Item{k}", [SQM.Asg("linkID", k), SQM.Asg("item0", a), SQM.Asg("item1", b),
                                                 SQM.Cls("CustomData", [SQM.Asg("type", "Sync")])]))
    _renumber(links)
    conn = SQM.Cls("Connections", [SQM.Cls("LinkIDProvider", [SQM.Asg("nextID", len(pairs))]), links])
    mission.items = [a for a in mission.items if not (isinstance(a, SQM.Cls) and a.name == "Connections")] + [conn]
    mission.dirty = True

    # --- providers and camera
    all_ids = []

    def ids(e):
        for it in _items(e):
            all_ids.append(int(it.get("id")))
            if it.get("dataType") in ("Layer", "Group"):
                ids(it.cls("Entities"))
    ids(ents)
    idp.set("nextID", max(all_ids) + 1)
    lip = edit.cls("LayerIndexProvider")
    if lip is not None:
        lip.set("nextID", int(lip.get("nextID")) + n_layers)
    cam = edit.cls("Camera")
    if cam is not None:
        c = td.size / 2
        cam.set("pos", [_fmt_f(c), _fmt_f(td.h(c, c) + 900.0), _fmt_f(c - 1200.0)], arr=True)
    return SQM.dump(root), dict(links=len(pairs), unit_links=len(unit_pairs), max_id=max(all_ids),
                                deleted=len(deleted), new_ids=next_id - first_id, units=len(units))


# =====================================================================================================
# 5) VALIDATOR (independent code path: re-reads the mission text, own thresholds, never calls the generator)
# =====================================================================================================

VCHK = dict(z_tol=0.5, atl_max=1.0, dry=0.5, slope_depot=0.10, slope_camp=0.15, slope_static=0.30, slope_spawn=0.35,
            start_p90=0.10, start_max=0.15, start_p90_100=0.12, start_p90_100_warn=0.08, hold_slope=0.05,
            nn_min=550.0, nn_warn=700.0, camp_depot=(50.0, 550.0), camp_camp=100.0, def_depot=550.0,
            sp_depot=(20.0, 450.0), start_depot=600.0, start_same_side=250.0, hold_depot=1500.0, hold_depot_min=800.0,
            hold_start=1000.0, hold_start_min=800.0, unit_hold=10.0, logic_hold=50.0,
            clear_depot=4.0, clear_camp=3.0, clear_static=1.5, clear_spawn=1.5, tree_depot=3.0, road_depot=6.0)


class VReport:
    def __init__(self):
        self.items = []

    def add(self, level, code, msg, key=""):
        self.items.append(dict(level=level, code=code, key=key, msg=msg))

    def err(self, code, msg, key=""):
        self.add("ERROR", code, msg, key)

    def warn(self, code, msg, key=""):
        self.add("WARN", code, msg, key)

    def info(self, code, msg, key=""):
        self.add("INFO", code, msg, key)

    def level(self, lv):
        return [i for i in self.items if i["level"] == lv]


def _v_kids(c):
    return [k for k in c.items if isinstance(k, SQM.Cls) and re.fullmatch(r"Item\d+", k.name)]


def _v_entities(e, path=(), group_side=None, out=None):
    """Flat list of entity records from Mission/Entities (layers and groups expanded)."""
    out = [] if out is None else out
    for it in _v_kids(e):
        dt = it.get("dataType")
        pi = it.cls("PositionInfo")
        pos = (pi.get("position") if pi is not None else None) or it.get("position")
        ang = pi.get("angles") if pi is not None else None
        attrs = it.cls("Attributes")
        rec = dict(cls=it, dt=dt, type=it.get("type"), name=it.get("name"), init=it.get("init") or "",
                   id=it.get("id"), path=path, side=it.get("side"), group_side=group_side,
                   x=float(pos[0]) if pos else None, y=float(pos[2]) if pos else None, z=float(pos[1]) if pos else None,
                   atl=float(it.get("atlOffset") or 0.0), yaw=float(ang[1]) if ang else 0.0,
                   playable=bool(attrs is not None and attrs.get("isPlayable")))
        out.append(rec)
        if dt == "Layer" and it.cls("Entities") is not None:
            _v_entities(it.cls("Entities"), path + (it.get("name") or "",), group_side, out)
        if dt == "Group" and it.cls("Entities") is not None:
            _v_entities(it.cls("Entities"), path, it.get("side"), out)
    return out


def _v_structure(root, R):
    if root.get("version") != 54:
        R.err("A_VERSION", f"version={root.get('version')} (se espera 54)")

    def walk(c, where):
        for k in c.items:
            if not isinstance(k, SQM.Cls):
                continue
            if k.name in ("Entities", "Links"):
                kids = [x for x in k.items if isinstance(x, SQM.Cls)]
                n = k.get("items")
                names = [x.name for x in kids]
                if n != len(kids) or names != [f"Item{i}" for i in range(len(kids))]:
                    R.err("A_ITEMS", f"{where}/{k.name}: items={n} pero hijos {names[:4]}...", where)
            walk(k, where + "/" + k.name)
    walk(root, "")


def check_mission(text, td=None, tcfg=None, profile="port", world=None):
    """Validate one mission.sqm text. profile 'cw' = author's CW missions (selftest), 'port' = generated ones.
    Returns (VReport, facts dict)."""
    R = VReport()
    facts = {}
    try:
        root = SQM.parse(text)
    except SyntaxError as e:
        R.err("A_PARSE", str(e))
        return R, facts
    if SQM.dump(root) != text:
        R.err("A_ROUNDTRIP", "leer y volver a escribir no da el mismo texto")
    _v_structure(root, R)
    mission = root.cls("Mission")
    ents = _v_entities(mission.cls("Entities"))
    # --- ids
    ids = [e["id"] for e in ents]
    if any(not isinstance(i, int) for i in ids):
        R.err("A_ID", "entidad sin id entero")
    ids = [i for i in ids if isinstance(i, int)]
    dup = [i for i, c in Counter(ids).items() if c > 1]
    if dup:
        R.err("A_ID_DUP", f"ids repetidos: {dup[:10]}")
    nxt = root.cls("EditorData").cls("ItemIDProvider").get("nextID")
    if ids and not (isinstance(nxt, int) and nxt > max(ids)):
        R.err("A_NEXTID", f"ItemIDProvider.nextID={nxt} no supera el id máximo {max(ids)}")
    byid = {e["id"]: e for e in ents}
    # --- links
    conn = mission.cls("Connections")
    links = []
    if conn is not None:
        lk = conn.cls("Links")
        items = _v_kids(lk) if lk is not None else []
        lids = [l.get("linkID") for l in items]
        if sorted(lids) != list(range(len(items))) or len(set(lids)) != len(lids):
            R.err("A_LINKID", "linkID no es 0..L-1 sin repetir")
        if lk is not None and (lk.get("items") != len(items) or conn.cls("LinkIDProvider").get("nextID") != len(items)):
            R.err("A_LINKCOUNT", f"Links.items={lk.get('items')}, LinkIDProvider.nextID="
                                 f"{conn.cls('LinkIDProvider').get('nextID')}, enlaces={len(items)}")
        seen = set()
        for l in items:
            a, b = l.get("item0"), l.get("item1")
            cd = l.cls("CustomData")
            if cd is None or cd.get("type") != "Sync":
                R.err("A_LINKTYPE", f"enlace {l.get('linkID')} no es Sync")
            if a not in byid or b not in byid:
                R.err("A_LINKREF", f"enlace {l.get('linkID')}: {a}->{b} apunta a un id que no existe")
                continue
            if a == b or (a, b) in seen or (b, a) in seen:
                R.err("A_LINKDUP", f"enlace {l.get('linkID')}: {a}->{b} repetido o a sí mismo")
            seen.add((a, b))
            links.append((a, b))
    adj = {}
    for a, b in links:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    # --- towns
    towns = [e for e in ents if e["dt"] == "Logic" and e["type"] == "LocationArea_F"]
    n = len(towns)
    tnames = Counter(e["name"] for e in towns)
    if set(tnames) != {f"Town{i}" for i in range(n)} or any(c > 1 for c in tnames.values()):
        R.err("B_TOWNK", f"los {n} LocationArea_F no se llaman Town0..Town{n - 1} sin huecos")
    town_objs = {id(e) for e in towns}
    others_k = [e["name"] for e in ents if id(e) not in town_objs and e["name"] and re.fullmatch(r"Town\d+", e["name"])]
    if others_k:
        R.err("B_TOWNK", f"otras entidades usan nombres TownK: {others_k[:5]}")
    display = {}
    for e in towns:
        m = TOWN_INIT_RE.match(e["init"])
        if not m:
            R.err("B_TOWNINIT", f"{e['name']}: init no tiene el formato esperado: {e['init'][:90]}", e["name"])
            continue
        nm, side, ssv, msv, val, rng = m.group(1), m.group(2), int(m.group(3)), int(m.group(4)), int(m.group(5)), m.group(6)
        if ssv > msv or val <= 0:
            R.err("B_TOWNSV", f"{nm}: startSV {ssv} > maxSV {msv} o value {val} <= 0", nm)
        if not nm.strip() or '"' in nm or "$STR" in nm:
            R.err("B_TOWNNAME", f"nombre de pueblo inválido {nm!r}", nm)
        if nm in display:
            R.err("B_TOWNNAME", f"nombre de pueblo repetido {nm!r}", nm)
        e["town_name"], e["range"] = nm, int(rng) if rng else 550
        e["sv"] = (ssv, msv, val)
        display[nm] = e
    town_ids = {e["id"] for e in towns}
    # --- children
    camps = [e for e in ents if e["dt"] == "Logic" and e["type"] == "LocationCamp_F"]
    spawns = [e for e in ents if e["dt"] == "Logic" and e["type"] == "LocationRespawnPoint_F"]
    defenses = [e for e in ents if e["dt"] == "Logic" and "cti_defense_kind" in e["init"]]
    orphan_sp = 0
    for kind, lst in (("camp", camps), ("defense", defenses), ("spawn", spawns)):
        for e in lst:
            t = [x for x in adj.get(e["id"], ()) if x in town_ids]
            e["town"] = byid[t[0]] if len(t) == 1 else None
            if len(t) != 1:
                if kind == "spawn" and not t:
                    orphan_sp += 1
                else:
                    R.err("B_ORPHAN", f"{kind} id={e['id']} enlazado a {len(t)} pueblos", f"{kind} id={e['id']}")
    if orphan_sp:
        R.err("B_ORPHAN_SPAWNS", f"{orphan_sp} LocationRespawnPoint_F sin pueblo", str(orphan_sp))
    for a, b in links:
        if a in town_ids and b in town_ids:
            R.err("B_TOWNLINK", f"enlace entre pueblos {a}-{b}")
    kinds = Counter()
    for e in defenses:
        m = re.search(r"cti_defense_kind',\s*\[(.*?)\]", e["init"])
        ks = re.findall(r"'(\w+)'", m.group(1)) if m else []
        if not ks or not set(ks) <= DEFENSE_KINDS:
            R.err("B_DEFKIND", f"defensa id={e['id']}: tipos {ks}", f"defense id={e['id']}")
        if profile == "port" and not set(ks) <= {"MG", "AT"}:
            R.err("B_DEFKIND", f"defensa id={e['id']}: el port solo usa MG/AT ({ks})")
        kinds.update(ks)
    if profile == "port":
        per_town = Counter(e["town"]["id"] for e in defenses if e.get("town"))
        for t in towns:
            if per_town.get(t["id"], 0) < 1:
                R.warn("B_DEFNONE", f"{t.get('town_name', t['name'])} no tiene defensas")
        if kinds["AT"] and not (2.0 <= kinds["MG"] / kinds["AT"] <= 4.0):
            R.warn("B_DEFRATIO", f"relación MG:AT {kinds['MG']}:{kinds['AT']} fuera de 2-4:1")
    # --- singletons
    named = Counter(e["name"] for e in ents if e["name"])
    for nm in ("CTI_WEST", "CTI_EAST", "CTI_Logic", "VIOC_ZEUS") + HOLDING_MARKERS:
        if named.get(nm, 0) != 1:
            R.err("B_SINGLE", f"{nm} aparece {named.get(nm, 0)} veces", nm)
    zeus = [e for e in ents if e["name"] == "VIOC_ZEUS"]
    if zeus and zeus[0]["type"] != "ModuleCurator_F":
        R.err("B_ZEUS", f"VIOC_ZEUS es {zeus[0]['type']}, no ModuleCurator_F (Zeus no funciona)", "VIOC_ZEUS")
    side_logic = {nm: e for e in ents for nm in ("CTI_WEST", "CTI_EAST") if e["name"] == nm}
    logic = [e for e in ents if e["name"] == "CTI_Logic"]
    templates = {}
    if logic:
        init = logic[0]["init"]
        if "Init_LocationMode.sqf" not in init:
            R.err("B_LOGICINIT", "CTI_Logic no ejecuta Init_LocationMode.sqf (los pueblos se quedan esperando)")
        for tpl, body in re.findall(r'setVariable \["Towns_Removed(\w+)",\s*\[(.*?)\]\]', init):
            names = re.findall(r'"([^"]*)"', body)
            templates[tpl] = names
            bad = [x for x in names if x not in display]
            if bad:
                R.err("B_TEMPLATE", f"Towns_Removed{tpl} nombra pueblos que no existen: {bad}", tpl)
            dups = sorted(x for x, c in Counter(names).items() if c > 1)
            if dups:  # harmless for `in` (Init_Location.sqf:15); found in the author's Altis/Livonia lists
                (R.err if profile == "port" else R.warn)("B_TEMPLATE_DUP", f"Towns_Removed{tpl} repite {dups}", tpl)
            if len(set(names)) >= max(n, 1):
                R.err("B_TEMPLATE", f"Towns_Removed{tpl} quita todos los pueblos", tpl)
            if tcfg:
                anchors = set(tcfg.get("anchors_west", [])) | set(tcfg.get("anchors_east", [])) | set(tcfg.get("keep_always", []))
                if anchors & set(names):
                    R.err("B_TEMPLATE", f"Towns_Removed{tpl} quita anclas: {sorted(anchors & set(names))}", tpl)
    # --- playable units
    units = [e for e in ents if e["dt"] == "Object" and e["group_side"] in ("West", "East")]
    cnt = Counter(u["group_side"] for u in units)
    facts["units"] = dict(cnt)
    if profile == "port" and (cnt["West"] != 16 or cnt["East"] != 16):
        R.err("B_UNITS", f"unidades jugables Oeste/Este = {cnt['West']}/{cnt['East']} (la plantilla tiene 16/16)")
    for u in units:
        lg = side_logic.get("CTI_WEST" if u["group_side"] == "West" else "CTI_EAST")
        other = side_logic.get("CTI_EAST" if u["group_side"] == "West" else "CTI_WEST")
        if lg is None or lg["id"] not in adj.get(u["id"], ()) or (other is not None and other["id"] in adj.get(u["id"], ())):
            R.err("B_UNITLINK", f"unidad id={u['id']} ({u['group_side']}) no está enlazada solo a su lógica de bando", f"unit {u['id']}")
    # --- start markers
    marks = {e["name"]: e for e in ents if e["dt"] == "Marker" and e["name"]}
    fam = {"": [], "-west": [], "-east": []}
    for nm in marks:
        m = SPAWN_RE.match(nm)
        if m:
            fam[m.group(1) or ""].append(int(m.group(2)))
    for f, idx in fam.items():
        if sorted(idx) != list(range(len(idx))):
            R.err("B_SPAWNGAP", f"cti-spawn{f}N no es contiguo desde 0: {sorted(idx)}", f)
    if 0 not in fam[""] or 1 not in fam[""]:
        R.err("B_SPAWN01", "faltan cti-spawn0 / cti-spawn1 (respaldo de Init_Server.sqf)")
    if len(fam[""]) > 51 or len(fam["-west"]) > 31 or len(fam["-east"]) > 31:
        R.err("B_SPAWNMAX", "demasiados marcadores de inicio (Init_Server lee 51 genéricos y 31 por bando)")
    gen = [marks[f"cti-spawn{i}"] for i in sorted(fam[""])]
    fw = [marks[f"cti-spawn-west{i}"] for i in sorted(fam["-west"])]
    fe = [marks[f"cti-spawn-east{i}"] for i in sorted(fam["-east"])]
    # --- atlOffset (no heightmap needed): towns and camps must sit on the ground
    for e in towns + camps:
        if abs(e["atl"]) > VCHK["atl_max"]:
            R.err("C_ATL", f"{e['type']} id={e['id']} tiene atlOffset={e['atl']:.1f} m (el búnker quedaría en el aire)",
                  f"{e['type']} id={e['id']}")
    for e in defenses:
        if abs(e["atl"]) > 15:
            R.warn("C_ATL_DEF", f"defensa id={e['id']} con atlOffset={e['atl']:.1f} m")
    facts.update(towns=n, camps=len(camps), defenses=len(defenses), spawn_points=len(spawns), links=len(links),
                 ids=len(ids), max_id=max(ids) if ids else None, kinds=dict(kinds), templates={k: len(v) for k, v in templates.items()},
                 markers=dict(generic=len(gen), west=len(fw), east=len(fe)))
    # --- geometry with the heightmap
    if td is not None:
        _v_geometry(R, td, towns, camps, defenses, spawns, gen, fw, fe, marks, units, side_logic, ents, facts)
    # --- start simulation
    if n and gen:
        tw = [(e.get("town_name", e["name"]), (e["x"], e["y"])) for e in towns]
        hfun = (lambda x, y: float(td.T.h(x, y))) if td is not None else None
        water = (lambda x, y: float(td.T.h(x, y)) <= 0.0) if td is not None else None
        sim = simulate_starts(tw, templates, [(m["x"], m["y"]) for m in fw], [(m["x"], m["y"]) for m in gen],
                              [(m["x"], m["y"]) for m in fe], hfun, water)
        facts["sim"] = sim
        for msg in sim["errors"]:
            (R.err if profile == "port" else R.info)("D_EMPTY", msg)
        for msg in sim["warnings"]:
            R.info("D_FALLBACK", msg)
        if profile == "port" and (fw or fe):
            full = [r for r in sim["rows"] if r["template"] == "Full" and r["start_town"] == 2000 and not r.get("empty")]
            if full:
                good = full[0]["snf1"]["good"]
                if good == 0:
                    R.err("D_SNF", "start_near_front (1.5-3 km): ningún par bueno con todos los pueblos y 2 km")
                elif good < 3:
                    R.warn("D_SNF", f"start_near_front (1.5-3 km): solo {good} pares buenos")
                if full[0]["snf1"]["reversed"]:
                    R.warn("D_SNF_REV", f"{full[0]['snf1']['reversed']} pares buenos con los bandos invertidos")
                sw = full[0]["pl6000"]["swap"]
                if sw is not None and sw > 0.15:
                    R.warn("D_SWAP", f"con 6 km, {sw:.0%} de los pares válidos invierten los bandos (cti-spawn0/1 en las dos listas)")
    return R, facts


def _v_geometry(R, td, towns, camps, defenses, spawns, gen, fw, fe, marks, units, side_logic, ents, facts):
    S = td.size
    main = td.main_component
    hard, trees = td.hard, td.trees

    def H(x, y):
        return float(td.T.h(x, y))

    def slope(x, y, r=10.0):
        return float(td.T.slope(x, y, r))

    skip = {"CTI_Logic", "HC_1", "HC_2", "HC_3", "VIOC_ZEUS"}
    for e in ents:
        if e["x"] is None or e["dt"] in ("Layer", "Group") or e["name"] in skip:
            continue
        if not (0 <= e["x"] <= S and 0 <= e["y"] <= S):
            R.err("C_BOUNDS", f"{e['name'] or e['type']} id={e['id']} fuera del mapa ({e['x']:.0f},{e['y']:.0f})")
            continue
        h = H(e["x"], e["y"])
        if abs(e["z"] - e["atl"] - h) > VCHK["z_tol"]:
            R.err("C_Z", f"{e['name'] or e['type']} id={e['id']}: Z={e['z']:.2f} pero el terreno está a {h:.2f}", str(e["id"]))
        if h <= VCHK["dry"] and e["dt"] in ("Logic", "Object", "Marker"):
            R.err("C_WATER", f"{e['name'] or e['type']} id={e['id']} en el agua (h={h:.2f})")
    depots = {}
    for t in towns:
        nm = t.get("town_name", t["name"])
        x, y = t["x"], t["y"]
        depots[nm] = (x, y)
        if td.component(x, y) != main:
            R.err("C_ISLAND", f"{nm}: el depósito no está en la isla principal")
        if slope(x, y) >= VCHK["slope_depot"]:
            R.err("C_SLOPE", f"{nm}: pendiente {slope(x, y):.0%} en el depósito")
        if td.min_h(x, y, 6.0) <= VCHK["dry"]:
            R.err("C_WATER", f"{nm}: el depósito toca el agua")
        if hard.clearance(x, y) < VCHK["clear_depot"] or trees.clearance(x, y) < VCHK["tree_depot"]:
            R.err("C_OBJECT", f"{nm}: depósito encima de un edificio, muro o árbol", nm)
        if td.road(x, y) < VCHK["road_depot"]:
            R.warn("C_ROAD", f"{nm}: depósito sobre el camino")
    names = list(depots)
    for nm in names:
        nn = min((dist(depots[nm], depots[o]) for o in names if o != nm), default=1e9)
        if nn < VCHK["nn_min"]:
            R.err("C_SPACING", f"{nm}: a {nn:.0f} m del pueblo más cercano (mínimo 550)")
        elif nn < VCHK["nn_warn"]:
            R.info("C_SPACING", f"{nm}: a {nn:.0f} m del pueblo más cercano")
    for kind, lst in (("camp", camps), ("defense", defenses), ("spawn", spawns)):
        for e in lst:
            t = e.get("town")
            if t is None:
                continue
            d = dist((e["x"], e["y"]), (t["x"], t["y"]))
            nm = t.get("town_name", t["name"])
            lim = {"camp": VCHK["camp_depot"], "defense": (0.0, VCHK["def_depot"]), "spawn": VCHK["sp_depot"]}[kind]
            if not (lim[0] <= d <= lim[1]):
                R.err("C_CHILDDIST", f"{kind} id={e['id']} de {nm} a {d:.0f} m del depósito ({lim[0]:.0f}-{lim[1]:.0f})")
            if d > t.get("range", 550) - 50 + 1:
                R.err("C_RANGE", f"{kind} id={e['id']} de {nm} fuera del rango del pueblo menos 50 m ({d:.0f} m)")
            closer = [o for o in names if o != nm and dist((e["x"], e["y"]), depots[o]) < d]
            if closer:
                R.warn("C_CHILDNEAR", f"{kind} id={e['id']} de {nm} queda más cerca de {closer[0]}")
            if td.component(e["x"], e["y"]) != main:
                R.err("C_ISLAND", f"{kind} id={e['id']} de {nm} fuera de la isla principal")
            sl = slope(e["x"], e["y"], 10.0 if kind == "camp" else 3.0)
            mx = {"camp": VCHK["slope_camp"], "defense": VCHK["slope_static"], "spawn": VCHK["slope_spawn"]}[kind]
            if sl >= mx:
                R.err("C_SLOPE", f"{kind} id={e['id']} de {nm}: pendiente {sl:.0%}")
            cl = {"camp": VCHK["clear_camp"], "defense": VCHK["clear_static"], "spawn": VCHK["clear_spawn"]}[kind]
            if hard.clearance(e["x"], e["y"]) < cl:
                R.err("C_OBJECT", f"{kind} id={e['id']} de {nm} encima de un edificio o muro")
            if kind == "camp" and trees.clearance(e["x"], e["y"]) < 2.0:
                R.err("C_OBJECT", f"campamento id={e['id']} de {nm} encima de un árbol")
    for i, a in enumerate(camps):
        for b in camps[i + 1:]:
            if dist((a["x"], a["y"]), (b["x"], b["y"])) < VCHK["camp_camp"]:
                R.err("C_CAMPGAP", f"campamentos {a['id']} y {b['id']} a menos de {VCHK['camp_camp']:.0f} m")
    # base starts (distinct positions)
    seen = []
    for m in gen + fw + fe:
        p = (round(m["x"], 1), round(m["y"], 1))
        if p in seen:
            continue
        seen.append(p)
        x, y = p
        if td.component(x, y) != main:
            R.err("C_START", f"{m['name']} fuera de la isla principal")
        if H(x, y) < 2.0 or td.wet(x, y, 40.0) > 0:
            R.err("C_START", f"{m['name']} pegado al agua")
        elif td.wet(x, y, 80.0, 20.0) > 0:
            R.warn("C_START", f"{m['name']}: agua a menos de 80 m")
        p90, mx = td.slope_stats(x, y, 60.0, 10.0)
        p90o, _mxo = td.slope_stats(x, y, 100.0, 10.0)
        if p90 >= VCHK["start_p90"] or mx >= VCHK["start_max"] or p90o >= VCHK["start_p90_100"]:
            R.err("C_START", f"{m['name']}: terreno inclinado (p90 {p90:.0%}, máx {mx:.0%} a 60 m; p90 {p90o:.0%} a 100 m)")
        elif p90o >= VCHK["start_p90_100_warn"]:
            R.info("C_START", f"{m['name']}: p90 {p90o:.0%} a 100 m (más de 8 %)")
        dd = min(dist(p, d) for d in depots.values()) if depots else 1e9
        if dd < VCHK["start_depot"]:
            R.err("C_START", f"{m['name']} a {dd:.0f} m de un depósito (mínimo 600)")
        if not (400 <= x <= td.size - 400 and 400 <= y <= td.size - 400):
            R.warn("C_START", f"{m['name']} a menos de 400 m del borde del mapa")
        if td.big.clearance(x, y, 60.0) < 20:
            R.err("C_START", f"{m['name']}: edificios a menos de 20 m")
    for side, lst in (("Oeste", fw), ("Este", fe)):
        pts = [(m["x"], m["y"]) for m in lst]
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                if dist(a, b) < VCHK["start_same_side"]:
                    R.err("C_STARTGAP", f"dos inicios del {side} a {dist(a, b):.0f} m")
    if gen and fw == [] and fe == [] and len(gen) >= 2:
        g = [(m["x"], m["y"]) for m in gen]
        dmax = max(dist(a, b) for i, a in enumerate(g) for b in g[i + 1:])
        if dist(g[0], g[1]) + 1 < dmax:
            R.warn("C_SPAWN01", "cti-spawn0/1 no son el par más lejano")
        if min(dist(a, b) for i, a in enumerate(g) for b in g[i + 1:]) < 1000:
            R.warn("C_STARTGAP", "marcadores genéricos a menos de 1000 m")
    elif len(gen) >= 2 and dist((gen[0]["x"], gen[0]["y"]), (gen[1]["x"], gen[1]["y"])) < 6000:
        R.warn("C_SPAWN01", "el par de respaldo cti-spawn0/1 está a menos de 6 km")
    # holding areas and units
    starts_xy = [(m["x"], m["y"]) for m in gen + fw + fe]
    for nm in HOLDING_MARKERS:
        m = marks.get(nm)
        if m is None:
            continue
        x, y = m["x"], m["y"]
        _p, mx = td.slope_stats(x, y, 20.0, 5.0)
        if mx >= VCHK["hold_slope"] or td.min_h(x, y, 20.0) < 2.0:
            R.err("C_HOLD", f"{nm}: no es llano y seco (pendiente máx {mx:.0%} a 20 m)")
        dd = min(dist((x, y), d) for d in depots.values()) if depots else 1e9
        if dd < VCHK["hold_depot_min"]:
            R.err("C_HOLD", f"{nm} a {dd:.0f} m de un pueblo (mínimo 800)")
        elif dd < VCHK["hold_depot"]:
            R.warn("C_HOLD", f"{nm} a {dd:.0f} m de un pueblo (se recomienda 1500)")
        ds = min((dist((x, y), s) for s in starts_xy), default=1e9)
        if ds < VCHK["hold_start_min"]:
            R.err("C_HOLD", f"{nm} a {ds:.0f} m de un inicio de base")
        elif ds < VCHK["hold_start"]:
            R.warn("C_HOLD", f"{nm} a {ds:.0f} m de un inicio de base")
        if hard.clearance(x, y) < 10.0:
            R.err("C_HOLD", f"{nm}: objetos a menos de 10 m")
    for u in units:
        m = marks.get("CTI_WestRespawn" if u["group_side"] == "West" else "CTI_EastRespawn")
        if m is not None and dist((u["x"], u["y"]), (m["x"], m["y"])) > VCHK["unit_hold"]:
            R.err("C_UNITPOS", f"unidad id={u['id']} a más de 10 m de su zona de espera")
    for nm, lg in side_logic.items():
        m = marks.get("CTI_WestRespawn" if nm == "CTI_WEST" else "CTI_EastRespawn")
        if m is not None and dist((lg["x"], lg["y"]), (m["x"], m["y"])) > VCHK["logic_hold"]:
            R.err("C_UNITPOS", f"{nm} a más de 50 m de su zona de espera")


def check_files(folder, R, world=None):
    """E) every file except mission.sqm byte-identical to the template; folder suffix = CfgWorlds class."""
    p = template_pbo()
    want = {e["name"].replace("\\", "/").lower(): e for e in p.entries}
    have = {}
    for dp, _dn, fn in os.walk(folder):
        for f in fn:
            if f == ".DS_Store":
                continue
            full = os.path.join(dp, f)
            have[os.path.relpath(full, folder).replace(os.sep, "/").lower()] = full
    missing = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    if missing:
        R.err("E_MISSING", f"faltan {len(missing)} archivos de la plantilla: {missing[:5]}")
    if extra:
        R.err("E_EXTRA", f"archivos que no están en la plantilla: {extra[:5]}")
    diff = []
    for k in sorted(set(want) & set(have)):
        if k == "mission.sqm":
            continue
        with open(have[k], "rb") as f:
            if f.read() != p.content(want[k]):
                diff.append(k)
    if diff:
        R.err("E_DIFF", f"{len(diff)} archivos distintos de la plantilla además de mission.sqm: {diff[:5]}")
    suffix = os.path.basename(os.path.normpath(folder)).rsplit(".", 1)[-1]
    if world is not None and suffix != world:
        R.err("E_WORLD", f"la carpeta termina en .{suffix} pero el mundo (CfgWorlds) es {world}")
    return dict(files=len(have), identical=len(set(want) & set(have)) - len(diff) - (1 if "mission.sqm" in have else 0))


# =====================================================================================================
# 6) START SIMULATION (replicates Server/Init/Init_Server.sqf:67-140 and the start_near_front patch)
# =====================================================================================================

SIM_TEMPLATES = ("Full", "XSmall", "Small", "Medium", "Large")
SIM_START_TOWN = (0, 1000, 2000, 3000, 4000)
SIM_PLACEMENT = (4000, 6000, 100000)


def _d3(a, b, hfun):
    """SQF `distance` between two ground positions (PositionAGL z=0 -> ASL via terrain height)."""
    d2 = math.hypot(a[0] - b[0], a[1] - b[1])
    if hfun is None:
        return d2
    return math.hypot(d2, hfun(a[0], a[1]) - hfun(b[0], b[1]))


def sim_lists(towns_xy, fam_w, generic, fam_e, start_town, hfun=None):
    """Side lists as built by Init_Server.sqf:67-109 (each entry: (x, y, origin) with origin W/E/G0/G1/Gk)."""
    def keep(p):
        if start_town <= 0:
            return True
        if not towns_xy:
            return False
        return min(_d3(p, t, hfun) for t in towns_xy) < start_town
    w = [(p[0], p[1], "W") for p in fam_w[:31] if keep(p)]
    g = [(p[0], p[1], f"G{k}") for k, p in enumerate(generic[:51]) if keep(p)]
    e = [(p[0], p[1], "E") for p in fam_e[:31] if keep(p)]
    return w + g, e + g


def snf_eval(wp, ep, towns_xy):
    """start_near_front `_vsnf_eval` for one pair -> (penalty, frontW, frontE, gap) for lo/hi = 1500/3000 and 1200/3500."""
    dw = [math.hypot(t[0] - wp[0], t[1] - wp[1]) for t in towns_xy]
    de = [math.hypot(t[0] - ep[0], t[1] - ep[1]) for t in towns_xy]
    n = len(towns_xy)
    half = n / 2.0
    keys = sorted(((dw[i] - de[i], i) for i in range(n)))
    near_w = min(range(n), key=lambda i: dw[i])  # SQF keeps the first index on ties
    near_e = min(range(n), key=lambda i: de[i])
    front_w = front_e = 1e6
    own_w = own_e = False
    for idx, (_k, t) in enumerate(keys):
        if idx < half:
            front_e = min(front_e, de[t])
            if t == near_w:
                own_w = True
        else:
            front_w = min(front_w, dw[t])
            if t == near_e:
                own_e = True
    gap = math.hypot(wp[0] - ep[0], wp[1] - ep[1])
    res = {}
    for mode, (lo, hi) in ((1, (1500, 3000)), (2, (1200, 3500))):
        pen = (max(0, lo - front_w) + max(0, front_w - hi) + max(0, lo - front_e) + max(0, front_e - hi)
               + 2 * max(0, 3000 - gap))
        if not own_w:
            pen += 2000
        if not own_e:
            pen += 2000
        res[mode] = (pen, round(front_w), round(front_e), round(gap))
    return res


def simulate_starts(towns, templates, fam_w, generic, fam_e, hfun=None, water=None):
    """All combinations of town template x CTI_BASE_START_TOWN x CTI_BASE_STARTUP_PLACEMENT, plus start_near_front.
    towns: [(name, (x, y))]; templates: {name: [removed names]}; fam_w/fam_e/generic: [(x, y)].
    Returns dict(rows=[...], errors=[...], warnings=[...], summary={...})."""
    rows, errors, warnings = [], [], []
    for tpl in SIM_TEMPLATES:
        removed = set(templates.get(tpl, [])) if tpl != "Full" else set()
        active = [p for n, p in towns if n not in removed]
        for st in SIM_START_TOWN:
            wl, el = sim_lists(active, fam_w, generic, fam_e, st, hfun)
            row = dict(template=tpl, start_town=st, n_west=len(wl), n_east=len(el), towns=len(active))
            if not wl or not el:
                errors.append(f"{tpl} + Start Near towns {st}: lista {'Oeste' if not wl else 'Este'} vacía "
                              f"(selectRandom devuelve nil y la base no se crea)")
                row["empty"] = True
                rows.append(row)
                continue
            total = len(wl) * len(el)
            for pl in SIM_PLACEMENT:
                valid = [(a, b) for a in wl for b in el if _d3(a, b, hfun) >= pl]
                p = len(valid) / total
                swapped = sum(1 for a, b in valid if a[2] == "G1" or b[2] == "G0") if fam_w or fam_e else 0
                p_fb = (1 - p) ** 299 if p < 1 else 0.0
                row[f"pl{pl}"] = dict(valid=len(valid), total=total, p_fallback=round(p_fb, 4),
                                      swap=round(swapped / len(valid), 3) if valid else None)
            # start_near_front (only with TOWNS: Starting Mode = 50/50)
            for mode in (1, 2):
                good, best = [], None
                for a in wl:
                    if water and water(a[0], a[1]):
                        continue
                    for b in el:
                        if water and water(b[0], b[1]):
                            continue
                        if math.hypot(a[0] - b[0], a[1] - b[1]) <= 1:
                            continue
                        r = snf_eval(a, b, active)[mode]
                        if r[0] <= 0:
                            good.append((a, b, r))
                        if best is None or r[0] < best[2][0]:
                            best = (a, b, r)
                rev = sum(1 for a, b, _r in good if a[2] == "G1" or b[2] == "G0") if fam_w or fam_e else 0
                layouts = sorted({(round(a[0]), round(a[1]), round(b[0]), round(b[1])) + r[1:] for a, b, r in good})
                row[f"snf{mode}"] = dict(good=len(good), reversed=rev, layouts=layouts[:12],
                                         best=None if good or best is None else
                                         dict(w=(round(best[0][0]), round(best[0][1])), e=(round(best[1][0]), round(best[1][1])),
                                              pen=round(best[2][0]), front_w=best[2][1], front_e=best[2][2], gap=best[2][3]))
            rows.append(row)
    # summary for the default lobby settings (Full, 2 km, 6 km) and the frente default (mode 1)
    summ = {}
    for r in rows:
        if r["template"] == "Full" and r["start_town"] == 2000 and not r.get("empty"):
            summ = dict(classic_6km=r["pl6000"], classic_4km=r["pl4000"], snf1=r["snf1"]["good"],
                        snf1_reversed=r["snf1"]["reversed"], snf2=r["snf2"]["good"])
    for r in rows:
        if r.get("empty"):
            continue
        if r["start_town"] in (1000, 2000) and r["pl6000"]["valid"] == 0:
            warnings.append(f"{r['template']} + Start Near towns {r['start_town']}: ningún par a 6 km; "
                            f"se usa el respaldo cti-spawn0/cti-spawn1")
    return dict(rows=rows, errors=errors, warnings=warnings, summary=summ)


def sim_table(sim):
    """Compact text table of a simulation."""
    out = ["plantilla  StartTown  listas W/E  6km: pares/total (respaldo, cruce)  4km  frente1.5-3: buenos (invertidos)  frente1.2-3.5"]
    for r in sim["rows"]:
        if r.get("empty"):
            out.append(f"{r['template']:9} {r['start_town']:5}      LISTA VACÍA ({r['n_west']}/{r['n_east']})")
            continue
        a, b = r["pl6000"], r["pl4000"]
        s1, s2 = r["snf1"], r["snf2"]
        extra = ""
        if s1["good"] == 0 and s1.get("best"):
            bb = s1["best"]
            extra = f"  [sin pares buenos; el mejor: frente O {bb['front_w']} m / E {bb['front_e']} m, bases {bb['gap']} m]"
        out.append(f"{r['template']:9} {r['start_town']:5}      {r['n_west']:2}/{r['n_east']:<2}       "
                   f"{a['valid']:3}/{a['total']:<3} ({a['p_fallback']:.2f}, {a['swap'] if a['swap'] is not None else '-'})"
                   f"        {b['valid']:3}/{b['total']:<3}   {s1['good']:3} ({s1['reversed']})                 {s2['good']:3}{extra}")
    return "\n".join(out)


# =====================================================================================================
# 7) COMMANDS
# =====================================================================================================

def cw_reference():
    """[(world, workshop id, mission.sqm text)] of the CW 2.0.6 reference missions (read-only)."""
    out = []
    for world, ws in CW_REFERENCE:
        hits = glob.glob(os.path.join(WORKSHOP, ws, "*_legacy.bin"))
        if len(hits) != 1:
            out.append((world, ws, None))
            continue
        p = Pbo(hits[0])
        out.append((world, ws, p.content(p.find("mission.sqm")).decode("latin-1")))
    return out


def cmd_selftest(quiet=False):
    """Round trip + check of the CW reference missions: only the known defects may appear (final_plan, regression)."""
    ok = True
    for world, ws, text in cw_reference():
        if text is None:
            say(f"FALTA  {world:17} (Workshop {ws} no está descargado)")
            ok = False
            continue
        rt = SQM.roundtrip(text)
        R, facts = check_mission(text, profile="cw", world=world)
        errs = {(i["code"], i["key"]) for i in R.level("ERROR")}
        expected = KNOWN_DEFECTS.get(world, set())
        good = rt and errs == expected
        ok &= good
        if not quiet or not good:
            say(f"{'OK   ' if good else 'MAL  '} {world:17} ida y vuelta {'idéntica' if rt else 'DISTINTA'}; "
                f"{facts.get('towns')} pueblos, {facts.get('camps')} campamentos, {facts.get('defenses')} defensas, "
                f"{facts.get('spawn_points')} puntos, {facts.get('links')} enlaces; "
                f"defectos conocidos: {sorted(k for _c, k in expected) or 'ninguno'}")
            for code, key in sorted(errs - expected):
                msg = next(i["msg"] for i in R.level("ERROR") if (i["code"], i["key"]) == (code, key))
                say(f"        NUEVO {code}: {msg}")
            for i in R.level("WARN"):
                say(f"        aviso {i['code']}: {i['msg']}")
            for code, key in sorted(expected - errs):
                say(f"        NO DETECTADO {code} {key}")
    if not quiet:
        say("selftest: " + ("todo bien" if ok else "HAY DIFERENCIAS"))
    return ok


def _world_check(tcfg):
    cw = read_cfg_worlds(tcfg)
    if cw.get("world") != tcfg["world"]:
        sys.exit(f"ERROR: el CfgWorlds del terreno es {cw.get('world')!r}, no {tcfg['world']!r}")
    return cw


def _load(key):
    tcfg = terrain_cfg(key)
    for m in tcfg.get("mods", []):
        if m.get("required") and not os.path.isdir(os.path.join(WORKSHOP, m["workshop"])):
            sys.exit(f"ERROR: falta descargar {m['title']} (Workshop {m['workshop']})")
    cw = _world_check(tcfg)
    td = TerrainData(tcfg, verbose=True)
    if abs(td.size - float(tcfg.get("world_size", td.size))) > 1:
        sys.exit(f"ERROR: el mapa mide {td.size:.0f} m, no {tcfg['world_size']}")
    return tcfg, cw, td


def describe_plan(plan, td):
    lines = []
    for k, t in enumerate(plan["towns"]):
        sv = TIERS[t["tier"]]
        lines.append(f"  Town{k:<2} {t['name']:16} {t['tier']} {sv[1]:3}/{sv[2]:4}  depósito ({t['pos'][0]:.0f},{t['pos'][1]:.0f}) "
                     f"a {dist(t['pos'], t['label']):3.0f} m de la etiqueta, h={td.h(*t['pos']):5.1f}  "
                     f"campamentos {len(t['camps'])}, defensas {len(t['defenses'])} "
                     f"({sum(1 for d in t['defenses'] if d[3] == 'MG')} MG/{sum(1 for d in t['defenses'] if d[3] == 'AT')} AT), "
                     f"puntos {len(t['spawns'])}" + (f", rango {t['range']}" if t.get("range") else "")
                     + (f"  [{'; '.join(t['notes'])}]" if t["notes"] else ""))
    lines.append("  Inicios:")
    for name, (x, y) in start_markers(plan):
        near = min(plan["towns"], key=lambda t: dist((x, y), t["pos"]))
        lines.append(f"    {name:16} ({x:.0f},{y:.0f})  {dist((x, y), near['pos']):.0f} m de {near['name']}")
    for nm, v in plan["holding"].items():
        lines.append(f"  {nm:16} ({v['pos'][0]:.0f},{v['pos'][1]:.0f})  {'isla' if v['info']['island'] else 'isla principal'}, "
                     f"{v['info']['depot']:.0f} m del pueblo más cercano")
    for tpl, names in plan["templates"].items():
        lines.append(f"  Towns_Removed{tpl:7} quita {len(names):2}: {', '.join(names)}")
    return "\n".join(lines)


def make_text(tcfg, td, generic_starts=0):
    p = template_pbo()
    tpl_text = p.content(p.find("mission.sqm")).decode("latin-1")
    plan = generate(tcfg, td, generic_starts=generic_starts)
    text, stats = rebuild_sqm(tpl_text, plan, td)
    return plan, text, stats


def cmd_plan(key, generic_starts=0):
    tcfg, cw, td = _load(key)
    t0 = time.time()
    plan, text, stats = make_text(tcfg, td, generic_starts)
    say(f"Plan para {tcfg['world']} ({cw.get('description')}), {len(plan['towns'])} pueblos ({time.time() - t0:.1f} s):")
    say(describe_plan(plan, td))
    R, facts = check_mission(text, td, tcfg, "port", tcfg["world"])
    say(f"\nmission.sqm: {len(text)} bytes, {stats['links']} enlaces, {stats['new_ids']} ids nuevos, {stats['deleted']} borrados")
    say("\nSimulación del sorteo de inicios (Init_Server.sqf:67-140 y start_near_front):")
    say(sim_table(facts["sim"]))
    _print_report(R)
    return 0 if not R.level("ERROR") else 1


def _print_report(R):
    for lv in ("ERROR", "WARN", "INFO"):
        items = R.level(lv)
        if items:
            say(f"{lv} ({len(items)}):")
            for i in items[:60]:
                say(f"  {i['code']}: {i['msg']}")


def folder_name(tcfg, version=None):
    return f"VIOBECTICW_{tcfg['key']}{f'_v{version}' if version else ''}.{tcfg['world']}"


def cmd_build(key, version=None, generic_starts=0):
    if not cmd_selftest(quiet=True):
        sys.exit("ERROR: selftest falla; no genero nada (final_plan F: regresión)")
    name = folder_name(terrain_cfg(key), version)
    dest = os.path.join(OUT_ROOT, name)
    if os.path.exists(dest):
        sys.exit(f"ERROR: ya existe {dest} (un juego de pueblos nuevo lleva --version N: la partida guardada se "
                 f"asocia al nombre de la carpeta)")
    tcfg, cw, td = _load(key)
    plan, text, stats = make_text(tcfg, td, generic_starts)
    R, facts = check_mission(text, td, tcfg, "port", tcfg["world"])
    if R.level("ERROR"):
        _print_report(R)
        sys.exit("ERROR: el validador encontró errores; no escribo la carpeta")
    os.makedirs(OUT_ROOT, exist_ok=True)
    tmp = os.path.join(OUT_ROOT, "." + name + ".tmp")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    p = template_pbo()
    for e in p.entries:
        target = os.path.join(tmp, *e["name"].split("\\"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        data = text.encode("latin-1") if e["name"].lower() == "mission.sqm" else p.content(e)
        with open(target, "wb") as f:
            f.write(data)
    os.rename(tmp, dest)
    say(f"Carpeta creada: {dest}")
    return cmd_check(dest, key, json_out=os.path.join(OUT_ROOT, f"{tcfg['id']}_report.json"), plan=plan, td=td,
                     stats=stats, md_out=os.path.join(OUT_ROOT, f"{tcfg['id']}_report.md"))


def cmd_check(folder, key=None, json_out=None, plan=None, td=None, stats=None, md_out=None):
    folder = os.path.abspath(folder)
    world = os.path.basename(os.path.normpath(folder)).rsplit(".", 1)[-1]
    key = key or terrain_for_world(world)
    tcfg = terrain_cfg(key) if key else None
    if tcfg is not None and td is None:
        td = TerrainData(tcfg)
    p = os.path.join(folder, "mission.sqm")
    with open(p, "rb") as f:
        text = f.read().decode("latin-1")
    R, facts = check_mission(text, td, tcfg, "port" if tcfg else "cw", world)
    cw = read_cfg_worlds(tcfg) if tcfg else {}
    facts["files"] = check_files(folder, R, cw.get("world") if tcfg else None)
    if tcfg is None:
        R.warn("C_NOTERRAIN", f"sin datos del terreno para {world}: no se revisan alturas, pendientes ni objetos")
    say(f"check {folder}: {len(R.level('ERROR'))} errores, {len(R.level('WARN'))} avisos, {len(R.level('INFO'))} notas")
    say(f"  {facts.get('towns')} pueblos, {facts.get('camps')} campamentos, {facts.get('defenses')} defensas {facts.get('kinds')}, "
        f"{facts.get('spawn_points')} puntos de aparición, {facts.get('links')} enlaces, {facts.get('ids')} ids (máx {facts.get('max_id')}), "
        f"marcadores {facts.get('markers')}, unidades {facts.get('units')}, archivos {facts['files']}")
    if "sim" in facts:
        say(sim_table(facts["sim"]))
    _print_report(R)
    if json_out:
        write_report(json_out, md_out, folder, tcfg, cw, R, facts, plan, td, stats)
    return 0 if not R.level("ERROR") else 1


def cmd_sim(folder, key=None):
    folder = os.path.abspath(folder)
    world = os.path.basename(os.path.normpath(folder)).rsplit(".", 1)[-1]
    key = key or terrain_for_world(world)
    td = TerrainData(terrain_cfg(key)) if key else None
    with open(os.path.join(folder, "mission.sqm"), "rb") as f:
        text = f.read().decode("latin-1")
    _R, facts = check_mission(text, td, terrain_cfg(key) if key else None, "port" if key else "cw", world)
    if "sim" not in facts:
        sys.exit("ERROR: la misión no tiene pueblos o marcadores de inicio")
    say(sim_table(facts["sim"]))
    full = [r for r in facts["sim"]["rows"] if r["template"] == "Full" and r["start_town"] == 2000 and not r.get("empty")]
    for r in full:
        for mode in (1, 2):
            say(f"start_near_front modo {mode}: {r[f'snf{mode}']['good']} pares buenos; disposiciones "
                f"(Oeste x,y, Este x,y, frente O, frente E, bases): {r[f'snf{mode}']['layouts']}")
    return 0


def cmd_survey(key):
    """Terrain facts to curate the JSON: Names, islands, big building clusters away from the labels."""
    tcfg = terrain_cfg(key)
    cw = read_cfg_worlds(tcfg)
    td = TerrainData(tcfg, verbose=True)
    say(f"CfgWorlds {cw['world']} ({cw.get('description')}), ILS {cw.get('ils')}, mapa {td.size:.0f} m")
    say(f"Tierra: isla principal {td.component_km2[td.main_component]:.1f} km2; otras: "
        + ", ".join(f"{v:.2f}" for k, v in sorted(td.component_km2.items(), key=lambda kv: -kv[1]) if k != td.main_component))
    labels = []
    for n in cw["names"]:
        if n["type"] in ("NameCityCapital", "NameCity", "NameVillage", "NameLocal", "Airport", "NameMarine"):
            x, y = n["pos"]
            labels.append((x, y))
            say(f"  {n['type']:16} {n['name']:20} ({x:.0f},{y:.0f}) h={td.h(x, y):6.1f} pendiente={td.slope(x, y):.0%} "
                f"agua100={td.wet(x, y, 100, 20):.0%} edificios250={td.buildings_near(x, y, 250)} "
                f"isla={'principal' if td.component(x, y) == td.main_component else td.component(x, y)}")
    # building clusters (links <= 150 m) at least 500 m from every label: candidate extra sites (bases, ports, farms)
    b = td.obj_kind == "building"
    bx, by, bm = td.obj_x[b], td.obj_y[b], td.obj_model[b]
    far = [i for i in range(len(bx)) if all(math.hypot(bx[i] - x, by[i] - y) >= 500 for x, y in labels)]
    parent = {i: i for i in far}

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a_ in far:
        for b_ in far:
            if a_ < b_ and math.hypot(bx[a_] - bx[b_], by[a_] - by[b_]) <= 150:
                parent[root(a_)] = root(b_)
    groups = {}
    for i in far:
        groups.setdefault(root(i), []).append(i)
    say("Grupos de edificios a más de 500 m de toda etiqueta (posibles sitios extra):")
    for g in sorted(groups.values(), key=len, reverse=True):
        if len(g) < 3:
            continue
        cx, cy = float(np.mean(bx[g])), float(np.mean(by[g]))
        kinds = Counter(m.lower().rsplit("\\", 1)[-1].rsplit(".", 1)[0] for m in bm[g]).most_common(4)
        say(f"  {len(g):3} edificios en ({cx:.0f},{cy:.0f}) "
            f"{'isla principal' if td.component(cx, cy) == td.main_component else 'otra isla'}: "
            + ", ".join(f"{k} x{v}" for k, v in kinds))
    return 0


# =====================================================================================================
# REPORTS
# =====================================================================================================

def write_report(json_out, md_out, folder, tcfg, cw, R, facts, plan, td, stats):
    with open(os.path.abspath(__file__), "rb") as f:
        tool_sha = hashlib.sha256(f.read()).hexdigest()
    rep = dict(generated=time.strftime("%Y-%m-%d %H:%M:%S"), tool="tools/vio_port.py", tool_sha256=tool_sha,
               template=dict(workshop=TEMPLATE_WS, entries=TEMPLATE_ENTRIES, mission_sqm_sha1=TEMPLATE_SQM_SHA1),
               folder=os.path.relpath(folder, PROJECT), world=tcfg["world"] if tcfg else None,
               terrain=dict(key=tcfg["id"], description=cw.get("description"), wrp_pbo=tcfg["wrp_pbo"],
                            size=td.size if td else None, objects=td.n_objects if td else None,
                            road_segments=len(td.T.segs) if td else None) if tcfg else None,
               counts={k: v for k, v in facts.items() if k not in ("sim",)},
               validator=dict(errors=R.level("ERROR"), warnings=R.level("WARN"), info=R.level("INFO")),
               mission_sqm_sha256=hashlib.sha256(open(os.path.join(folder, "mission.sqm"), "rb").read()).hexdigest())
    if plan is not None:
        rep["towns"] = [dict(town=f"Town{k}", name=t["name"], tier=t["tier"], startSV_maxSV_value=TIERS[t["tier"]],
                             range=t.get("range"), label=t["label"], depot=[round(t["pos"][0], 1), round(t["pos"][1], 1)],
                             depot_h=round(td.h(*t["pos"]), 2), depot_from_label=round(dist(t["pos"], t["label"])),
                             nearest_town_m=round(t["nn"]), camps=[[round(c[0], 1), round(c[1], 1)] for c in t["camps"]],
                             defenses=[[round(d[0], 1), round(d[1], 1), d[3]] for d in t["defenses"]],
                             spawn_points=len(t["spawns"]), anchor=("west" if t["name"] in plan["anchors"]["west"] else
                                                                  "east" if t["name"] in plan["anchors"]["east"] else None),
                             notes=t["notes"], source=t.get("source")) for k, t in enumerate(plan["towns"])]
        rep["starts"] = [dict(marker=nm, pos=[round(x, 1), round(y, 1)]) for nm, (x, y) in start_markers(plan)]
        rep["start_details"] = {side: [dict(target=list(s["target"]), pos=[round(s["pos"][0], 1), round(s["pos"][1], 1)],
                                            **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s["info"].items()})
                                       for s in plan[side]] for side in ("west", "east")}
        rep["holding"] = {k: dict(pos=[round(v["pos"][0], 1), round(v["pos"][1], 1)],
                                  **{kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v["info"].items()})
                          for k, v in plan["holding"].items()}
        rep["templates"] = plan["templates"]
        rep["anchors"] = plan["anchors"]
        rep["keep_always"] = tcfg.get("keep_always", [])
        rep["rebuild"] = stats
    if "sim" in facts:
        rep["simulation"] = dict(summary=facts["sim"]["summary"], errors=facts["sim"]["errors"],
                                 warnings=facts["sim"]["warnings"], rows=facts["sim"]["rows"], table=sim_table(facts["sim"]))
    rep["catalog_params"] = tcfg.get("catalog_params", {}) if tcfg else {}
    if plan is not None and td is not None:
        png = render_map(os.path.splitext(json_out)[0].replace("_report", "") + "_map.png", plan, td,
                         f"{tcfg.get('map_es', tcfg['world'])} ({tcfg['world']})")
        if png:
            rep["map_png"] = os.path.relpath(png, PROJECT)
            say(f"Mapa: {png}")
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    say(f"Informe: {json_out}")
    if md_out and plan is not None:
        with open(md_out, "w", encoding="utf-8") as f:
            f.write(report_md(rep, plan, tcfg, td, facts))
        say(f"Resumen: {md_out}")


def _where(p, plan):
    near = min(plan["towns"], key=lambda t: dist(p, t["pos"]))
    b = bearing(near["pos"], p)
    rosa = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"][int(((b + 22.5) % 360) // 45)]
    return f"{dist(p, near['pos']) / 1000:.1f} km al {rosa} de {near['name']}"


def report_md(rep, plan, tcfg, td, facts):
    """Short Spanish summary for the user: towns, where the bases start, holding areas, known limits."""
    tipo = {"L": "grande", "M": "mediano", "S": "chico"}
    n = len(plan["towns"])
    L = [f"# {tcfg.get('map_es', tcfg['world'])} para VIO-BECTI-CW: misión base generada", "",
         f"Generada el {rep['generated']} por `tools/vio_port.py` a partir de la misión CW Malden 2.0.6 (Workshop {TEMPLATE_WS}). "
         f"Carpeta: `{rep['folder']}`. Solo cambia `mission.sqm`; los otros {TEMPLATE_ENTRIES - 1} archivos son idénticos a la plantilla.", "",
         f"Validador: {len(rep['validator']['errors'])} errores, {len(rep['validator']['warnings'])} avisos."
         + (f" Mapa: `{rep['map_png']}`." if rep.get("map_png") else ""), "",
         "## Pueblos", "",
         "| # | Pueblo | Tamaño (SV máx / valor) | Campamentos | Defensas | Nota |", "|---|---|---|---|---|---|"]
    keep = set(tcfg.get("keep_always", []))
    for k, t in enumerate(plan["towns"]):
        sv = TIERS[t["tier"]]
        anc = ("ancla Oeste" if t["name"] in plan["anchors"]["west"] else "ancla Este" if t["name"] in plan["anchors"]["east"]
               else "siempre activo" if t["name"] in keep else "")
        L.append(f"| {k} | {t['name']} | {tipo[t['tier']]} ({sv[1]} / {sv[2]}) | {len(t['camps'])} | {len(t['defenses'])} | {anc} |")
    L += ["", "Las anclas" + (f" (y {', '.join(sorted(keep))})" if keep else "") + " nunca se quitan con 'TOWNS: Amount'. "
          f"Extra Small deja {n - len(plan['templates']['XSmall'])} pueblos, Small {n - len(plan['templates']['Small'])}, "
          f"Medium {n - len(plan['templates']['Medium'])} y Large {n - len(plan['templates']['Large'])}.", ""]
    if plan.get("generic"):
        L += ["## Dónde empiezan las bases", "", f"Modo genérico: {len(plan['generic'])} marcadores cti-spawnN, cualquiera para cualquier bando.", ""]
    else:
        L += ["## Dónde empiezan las bases", "", "**Oeste (azul):**"]
        L += [f"- {'principal (respaldo) ' if k == 0 else ''}{_where(s['pos'], plan)}" for k, s in enumerate(plan["west"])]
        L += ["", "**Este (rojo):**"]
        L += [f"- {'principal (respaldo) ' if k == 0 else ''}{_where(s['pos'], plan)}" for k, s in enumerate(plan["east"])]
        far = [dist(w["pos"], e["pos"]) for w in plan["west"] for e in plan["east"] if dist(w["pos"], e["pos"]) >= 6000]
        sm = facts["sim"]["summary"]
        L.append("")
        if far:
            L.append(f"- Con los valores del lobby por defecto (Start Near towns 2 KM, Start-up Placement 6 KM) la misión sortea entre "
                     f"{sm['classic_6km']['valid']} pares de inicios separados {min(far) / 1000:.1f}-{max(far) / 1000:.1f} km. "
                     f"En {sm['classic_6km']['swap']:.0%} de los sorteos los bandos salen cambiados, porque cti-spawn0/1 "
                     f"entran en las dos listas (Init_Server.sqf).")
        full = [r for r in facts["sim"]["rows"] if r["template"] == "Full" and r["start_town"] == 2000 and not r.get("empty")]
        if full:
            lay = full[0]["snf1"]["layouts"]
            L.append(f"- En los escenarios \"frente\" (parche start_near_front) hay {sm['snf1']} pares con el primer pueblo enemigo "
                     f"a 1.5-3 km ({sm['snf2']} con la opción 1.2-3.5 km):")
            for wx, wy, ex, ey, fw, fe, gap in lay:
                L.append(f"  - Oeste {_where((wx, wy), plan)}; Este {_where((ex, ey), plan)} (bases a {gap / 1000:.1f} km; "
                         f"primer pueblo enemigo a {fw / 1000:.1f} y {fe / 1000:.1f} km)")
        L.append(f"- Con 'Use Default' siempre se usa el par principal: Oeste {_where(plan['west'][0]['pos'], plan)}, "
                 f"Este {_where(plan['east'][0]['pos'], plan)}.")
        L.append("")
    L += ["## Zonas de espera y prisión", ""]
    for nm, v in plan["holding"].items():
        L.append(f"- {nm}: {'isla sin acceso por tierra' if v['info']['island'] else 'isla principal'} en "
                 f"({v['pos'][0]:.0f}, {v['pos'][1]:.0f}), a {v['info']['depot'] / 1000:.1f} km del pueblo más cercano.")
    L += ["", "## Límites conocidos", "",
          f"- Nada se probó dentro del juego. Las posiciones salen del mapa de alturas y de los {f'{td.n_objects:,}'.replace(',', '.')} "
          "objetos del terreno leídos del .wrp: depósitos, campamentos y defensas quedan lejos de edificios, muros y árboles según "
          "radios aproximados por modelo, no según la forma real de cada edificio.",
          "- Las bases usan una regla de pendiente algo más permisiva que la del diseño: p90 < 10 % y máx. < 15 % a 60 m, "
          "p90 < 12 % a 100 m."]
    L += [f"- {x}" for x in tcfg.get("known_limits_es", [])]
    L += ["- Si se cambian los pueblos o los inicios, generar con `--version N` (otra carpeta): la partida guardada se asocia "
          "al nombre de la carpeta y cargaría los pueblos por índice.", ""]
    return "\n".join(L)


def render_map(png, plan, td, title):
    """Optional overview image (needs matplotlib; skipped without it). Returns the path or None."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    e = td.T.e
    S = td.size
    fig, ax = plt.subplots(figsize=(13, 13), dpi=80)
    ax.imshow(np.where(e > 0, e, np.nan), origin="lower", extent=[0, S, 0, S], cmap="terrain", vmin=-60, vmax=float(e.max()) + 20)
    ax.set_facecolor("#9ec5e8")
    k = td.obj_kind
    ax.scatter(td.obj_x[k == "tree"], td.obj_y[k == "tree"], s=0.03, c="darkgreen", linewidths=0)
    ax.scatter(td.obj_x[k == "building"], td.obj_y[k == "building"], s=2, c="dimgrey", linewidths=0)
    for x1, y1, x2, y2 in td.T.segs:
        ax.plot([x1, x2], [y1, y2], "-", c="#5a4632", lw=0.6)
    tier_ms = {"L": 13, "M": 10, "S": 8}
    for k_, t in enumerate(plan["towns"]):
        ax.plot(*t["pos"], "o", c="gold", mec="k", ms=tier_ms[t["tier"]], zorder=5)
        for c in t["camps"]:
            ax.plot(*c, "s", c="orange", mec="k", ms=4, zorder=4)
        ax.text(t["pos"][0] + 90, t["pos"][1] + 60, f"{t['name']}", fontsize=10, weight="bold", zorder=6)
    for nm, (x, y) in start_markers(plan):
        if nm.startswith("cti-spawn-west"):
            ax.plot(x, y, "^", c="#1f5fd1", mec="w", ms=14, zorder=7)
        elif nm.startswith("cti-spawn-east"):
            ax.plot(x, y, "v", c="#d12f1f", mec="w", ms=14, zorder=7)
        elif plan.get("generic"):
            ax.plot(x, y, "D", c="purple", mec="w", ms=10, zorder=7)
    for nm, v in plan["holding"].items():
        ax.plot(*v["pos"], "*", c="magenta" if nm == "Prison" else "white", mec="k", ms=15, zorder=7)
        ax.text(v["pos"][0] + 90, v["pos"][1] - 160, nm, fontsize=9, zorder=7)
    ax.set_xlim(0, S)
    ax.set_ylim(0, S)
    ax.set_xticks(np.arange(0, S + 1, 1000))
    ax.set_yticks(np.arange(0, S + 1, 1000))
    ax.grid(alpha=0.25)
    ax.set_title(title + " — depósitos (amarillo), campamentos (naranja), inicios Oeste (azul) y Este (rojo), espera (estrellas)")
    fig.savefig(png, bbox_inches="tight")
    plt.close(fig)
    return png


def main(argv=None):
    ap = argparse.ArgumentParser(description="Port de VIO-BECTI-CW a terrenos nuevos")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    s = sub.add_parser("survey")
    s.add_argument("terrain")
    s = sub.add_parser("plan")
    s.add_argument("terrain")
    s.add_argument("--generic-starts", type=int, default=0)
    s = sub.add_parser("build")
    s.add_argument("terrain")
    s.add_argument("--version", type=int)
    s.add_argument("--generic-starts", type=int, default=0)
    s = sub.add_parser("check")
    s.add_argument("folder")
    s.add_argument("--terrain")
    s.add_argument("--json")
    s = sub.add_parser("sim")
    s.add_argument("folder")
    s.add_argument("--terrain")
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        return 0 if cmd_selftest() else 1
    if a.cmd == "survey":
        return cmd_survey(a.terrain)
    if a.cmd == "plan":
        return cmd_plan(a.terrain, a.generic_starts)
    if a.cmd == "build":
        return cmd_build(a.terrain, a.version, a.generic_starts)
    if a.cmd == "check":
        return cmd_check(a.folder, a.terrain, a.json)
    if a.cmd == "sim":
        return cmd_sim(a.folder, a.terrain)
    return 2


if __name__ == "__main__":
    sys.exit(main())
