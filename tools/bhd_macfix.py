#!/usr/bin/env python3
"""bhd_macfix.py — copia local de BLACK HAWK DOWN (Workshop 2323185675) que funcione en el Mac.

El problema (2026-10-12): en el Mac la campaña no encuentra sus propios archivos cuando la misión los pide
con ruta relativa ("Script new_script\\plot_scripts\\start.sqf not found", "Picture pictures\\overview.paa
not found"), aunque están dentro de campaign.pbo. Con ruta absoluta sí los encuentra (en el menú se ve
campaign\\overview\\overview_1.paa). campaign.pbo es el único de los 1074 PBO de la línea 3 sin propiedad
"prefix", y su carpeta de campaña tiene un solo nivel ("campaign"). La campaña oficial East Wind, que en este
Mac carga rutas relativas, usa un PBO con prefijo y una carpeta de varios niveles ("A3\\Missions_F_EPA\\Campaign").
Esta copia imita esa estructura sin cambiar ningún archivo de las misiones.

Qué arma (nunca toca el Workshop; cada carpeta, archivo y symlink queda en install_manifest.tsv para undo.sh):
  ~/ArmaMods/@BlackHawkDown_Mac/
    addons/bhd_mac_campaign.pbo   la campaña con prefijo "bhd_mac_campaign" y todo dentro de "Campaign\\";
                                  solo cambian config.cpp y las rutas de las imágenes del menú en
                                  Campaign\\Description.ext
    addons/bhd_mac_fixes.pbo      material menos brillante para los cascos Pro-Tec de CUP, que se ven
                                  plateados (fallo de CUP que el autor de BHD reconoce en los comentarios)
    addons/helmet.pbo, resurs.pbo, m16_a2.pbo y los logos: symlinks a los originales del Workshop
    mod.cpp                       nombre visible en el juego
Uso:
  bhd_macfix.py [--dry-run] build    arma la carpeta (aborta si ya existe)
  bhd_macfix.py remove               borra lo que armó build (comprueba huellas), para volver a armarlo
"""
import hashlib
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pbo_tool  # noqa: E402

PROJECT = os.path.dirname(HERE)
MANIFEST = os.path.join(PROJECT, "install_manifest.tsv")
WS = os.path.expanduser("~/Library/Application Support/Steam/steamapps/workshop/content/107410/2323185675")
GAME = os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Arma 3")
CUP_USARMY = os.path.join(os.path.realpath(os.path.expanduser("~/ArmaMods/@CUP_Units")), "addons",
                          "cup_creatures_people_military_usarmy.pbo")
DEST = os.path.expanduser("~/ArmaMods/@BlackHawkDown_Mac")
CAMPAIGN_PREFIX = "bhd_mac_campaign"
FIXES_PREFIX = "bhd_mac_fixes"
LINKED = ["helmet.pbo", "resurs.pbo", "m16_a2.pbo"]  # se usan tal cual
LOGOS = ["logo_bhd_ca.paa", "logo_bhd_o_ca.paa"]

CAMPAIGN_CONFIG = f"""class CfgPatches
{{
	class BHD_Mac_Campaign
	{{
		name = "BLACK HAWK DOWN - campana (copia local para Mac)";
		author = "BIG_DOG";
		units[] = {{}};
		weapons[] = {{}};
		requiredVersion = 0.1;
		requiredAddons[] = {{}};
	}};
}};
class CfgMissions
{{
	class Campaigns
	{{
		class BHD
		{{
			directory = "{CAMPAIGN_PREFIX}\\Campaign";
		}};
	}};
}};
"""

# Cascos Pro-Tec de CUP (las variantes _Pro y _Pro_gog heredan de estas cuatro).
PROTEC = ["CUP_H_USArmy_Helmet_Protec", "CUP_H_USArmy_Helmet_Protec_Gog",
          "CUP_H_USArmy_Helmet_Protec_Gog_Strb", "CUP_H_USArmy_Helmet_Protec_NVG"]
MATTE_PATH = f"\\{FIXES_PREFIX}\\data\\protec_base_matte.rvmat"
FIXES_CONFIG = (
    "class CfgPatches\n{\n\tclass BHD_Mac_Fixes\n\t{\n"
    '\t\tname = "BHD Mac: cascos Pro-Tec de CUP sin brillo plateado";\n'
    "\t\tunits[] = {};\n\t\tweapons[] = {};\n\t\trequiredVersion = 2.0;\n"
    '\t\trequiredAddons[] = {"CUP_Creatures_Military_USArmy"};\n\t};\n};\n'
    "class CfgWeapons\n{\n\tclass ItemCore;\n"
    + "".join(f'\tclass {c}: ItemCore\n\t{{\n\t\thiddenSelectionsMaterials[] = {{"{MATTE_PATH}"}};\n\t}};\n'
              for c in PROTEC)
    + "};\n")

# protec_base.rvmat de CUP con el brillo del casco de skate vanilla (C_Helmet_Skate: fresnel(1,0.7), env_co).
# El mapa SMDI de CUP tiene ~2.5 veces más especular que el vanilla (canal G: 49 contra 20), por eso
# specular baja de 1.0 a 0.2 en vez de 0.5.
CUP_PROTEC = "cup\\creatures\\people\\military\\cup_creatures_people_military_usarmy\\data\\protec\\"
UV = ('  uvSource = "tex";\n  class uvTransform {\n    aside[] = {1, 0, 0};\n    up[] = {0, 1, 0};\n'
      '    dir[] = {0, 0, 0};\n    pos[] = {0, 0, 0};\n  };\n')


def stage(n, tex, extra=""):
    return f'class Stage{n} {{\n  texture = "{tex}";\n{extra}{UV}}};\n'


MATTE_RVMAT = (
    "ambient[] = {1, 1, 1, 1};\ndiffuse[] = {1, 1, 1, 1};\nforcedDiffuse[] = {0, 0, 0, 1};\n"
    "emmisive[] = {0, 0, 0, 0};\nspecular[] = {0.2, 0.2, 0.2, 1};\nspecularPower = 50;\n"
    'PixelShaderID = "Super";\nVertexShaderID = "Super";\n'
    + stage(1, CUP_PROTEC + "protec_base_nohq.paa")
    + stage(2, "#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)")
    + stage(3, "#(argb,8,8,3)color(0,0,0,0,MC)")
    + stage(4, CUP_PROTEC + "protec_base_as.paa")
    + stage(5, CUP_PROTEC + "protec_base_smdi.paa")
    + stage(6, "#(ai,64,64,1)fresnel(1,0.7)")
    + stage(7, "a3\\data_f\\env_co.paa", '  useWorldEnvMap = "true";\n'))

MOD_CPP = f"""name = "BLACK HAWK DOWN v2.0 (copia local para Mac)";
picture = "{LOGOS[0]}";
logo = "{LOGOS[0]}";
logoOver = "{LOGOS[1]}";
tooltip = "BHD (Mac)";
author = "BIG_DOG";
overview = "Copia local de la campana BLACK HAWK DOWN (Workshop 2323185675) reempaquetada para el Mac, mas cascos Pro-Tec de CUP sin brillo plateado.";
"""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def campaign_entries():
    src = pbo_tool.Pbo(os.path.join(WS, "Addons", "campaign.pbo"))
    now = int(time.time())
    out = [("config.cpp", CAMPAIGN_CONFIG.encode("utf-8"), now)]
    changed = 0
    for e in src.entries:
        low = e["name"].lower()
        if low == "config.cpp":
            continue
        data = src.content(e)
        if low == "description.ext":
            old, new = b"campaign\\overview\\", f"{CAMPAIGN_PREFIX}\\Campaign\\overview\\".encode()
            changed = data.count(old)
            if changed != 15:  # la campaña + loadScreen y overviewPicture de las 7 misiones
                sys.exit(f"ERROR: esperaba 15 rutas de imagen en Description.ext y hay {changed}")
            data = data.replace(old, new)
        if low == "stringtable.xml":  # también en la raíz del PBO, como el original
            out.append(("stringtable.xml", data, e["ts"]))
        out.append(("Campaign\\" + e["name"], data, e["ts"]))
    return src, out, changed


def fixes_entries():
    now = int(time.time())
    return [("config.cpp", FIXES_CONFIG.encode("utf-8"), now),
            ("data\\protec_base_matte.rvmat", MATTE_RVMAT.encode("utf-8"), now)]


def check_textures():
    """Las texturas que nombra el material nuevo existen (en CUP y en el juego)."""
    cup = {e["name"].lower() for e in pbo_tool.Pbo(CUP_USARMY).entries}
    for n in ("protec_base_nohq.paa", "protec_base_as.paa", "protec_base_smdi.paa"):
        if f"data\\protec\\{n}" not in cup:
            sys.exit(f"ERROR: CUP ya no trae data\\protec\\{n}")
    data_f = {e["name"].lower() for e in pbo_tool.Pbo(os.path.join(GAME, "Addons", "data_f.pbo")).entries}
    if "env_co.paa" not in data_f:
        sys.exit("ERROR: el juego no trae a3\\data_f\\env_co.paa")


def verify_campaign(src, path):
    """El PBO nuevo es válido y trae byte a byte todos los archivos de las misiones."""
    new = pbo_tool.Pbo(path)
    if not new.sha1_ok or dict(new.props).get("prefix") != CAMPAIGN_PREFIX:
        sys.exit(f"ERROR: {path} quedó mal armado")
    byname = {e["name"].lower(): e for e in new.entries}
    same = 0
    for e in src.entries:
        low = e["name"].lower()
        if low in ("config.cpp", "description.ext"):
            continue
        if new.raw(byname["campaign\\" + low]) != src.content(e):
            sys.exit(f"ERROR: {e['name']} no quedó idéntico")
        same += 1
    return len(new.entries), same


def manifest_add(kind, target, extra):
    with open(MANIFEST, "a") as f:
        f.write(f"{kind}\t{target}\t{extra}\n")


def make_dir(p):
    os.mkdir(p)
    manifest_add("dir", p, "-")


def make_file(p, data):
    pbo_tool.write_new(p, data)
    manifest_add("file", p, sha256(data))


def make_link(target, link):
    if not os.path.exists(target):
        sys.exit(f"ERROR: no existe {target}")
    os.symlink(target, link)
    manifest_add("symlink", link, target)


def cmd_build(dry):
    if os.path.lexists(DEST):
        sys.exit(f"ERROR: ya existe {DEST} (usa 'remove' antes de volver a armarlo)")
    check_textures()
    src, centries, changed = campaign_entries()
    campaign = pbo_tool.build_pbo(centries, [("prefix", CAMPAIGN_PREFIX)])
    fixes = pbo_tool.build_pbo(fixes_entries(), [("prefix", FIXES_PREFIX)])
    print(f"campaña: {len(centries)} entradas, {len(campaign) / 1e6:.1f} MB; "
          f"rutas de imagen cambiadas en Description.ext: {changed}")
    print(f"arreglo de cascos: {len(fixes)} bytes ({len(PROTEC)} clases Pro-Tec)")
    if dry:
        print("(simulación: no se escribió nada)")
        return
    addons = os.path.join(DEST, "addons")
    make_dir(DEST)
    make_dir(addons)
    make_file(os.path.join(addons, "bhd_mac_campaign.pbo"), campaign)
    make_file(os.path.join(addons, "bhd_mac_fixes.pbo"), fixes)
    for n in LINKED:
        make_link(os.path.join(WS, "Addons", n), os.path.join(addons, n))
    for n in LOGOS:
        make_link(os.path.join(WS, n), os.path.join(DEST, n))
    make_file(os.path.join(DEST, "mod.cpp"), MOD_CPP.encode("utf-8"))
    total, same = verify_campaign(src, os.path.join(addons, "bhd_mac_campaign.pbo"))
    print(f"verificado: {total} entradas, {same} archivos de misión idénticos al original, SHA1 OK")
    dlls = [os.path.join(dp, f) for dp, _, fs in os.walk(DEST, followlinks=True)
            for f in fs if f.lower().endswith(".dll")]
    print(f"DLL en {DEST}: {len(dlls)}")
    print(f"listo: {DEST}")


def cmd_remove():
    """Deshace build: borra solo lo registrado bajo DEST cuyo contenido no cambió."""
    keep, mine = [], []
    with open(MANIFEST) as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            (mine if len(parts) == 3 and (parts[1] == DEST or parts[1].startswith(DEST + "/")) else keep).append(line)
    for line in reversed(mine):
        kind, target, extra = line.rstrip("\n").split("\t")
        if kind == "file":
            with open(target, "rb") as fh:
                if sha256(fh.read()) != extra:
                    sys.exit(f"ERROR: {target} cambió; no lo borro")
            os.remove(target)
        elif kind == "symlink":
            if not os.path.islink(target):
                sys.exit(f"ERROR: {target} no es un symlink")
            os.remove(target)
        elif kind == "dir":
            leftovers = [n for n in os.listdir(target) if n != ".DS_Store"]
            if leftovers:
                sys.exit(f"ERROR: {target} tiene archivos que no son míos: {leftovers}")
            shutil.rmtree(target)
        print(f"borrado: {target}")
    with open(MANIFEST, "w") as f:
        f.writelines(keep)


def main(argv):
    dry = "--dry-run" in argv
    args = [a for a in argv[1:] if a != "--dry-run"]
    if args == ["build"]:
        return cmd_build(dry)
    if args == ["remove"] and not dry:
        return cmd_remove()
    sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
