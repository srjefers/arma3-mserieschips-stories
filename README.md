# Arma 3 on M-series Macs: Warfare stories

Single-player Warfare (CTI) campaigns for **Arma 3 on Apple Silicon Macs** (official Mac port 2.22). They are built on
[VIO-BECTI-CW 2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799271) and inspired by the old Arma 2
Warfare / "Welcome to War" games. You play against the AI: lead a squad, capture towns, build bases, and win the island.

> 🇪🇸 **En español:** todo el código, los comentarios y la documentación de `docs/` están en español. Hay un resumen al final.

This repo does **not** ship the VIO-BECTI mission or any mod. It ships **patches and tools**: you subscribe to the
original mission on the Steam Workshop, and `tools/vio_build.py` applies the patches to your copy, then installs the
result in your `mpmissions` folder. See [NOTICE.md](NOTICE.md).

## What's in the missions

There are 31 configured scenarios on Malden, Livonia, Takistan, Altis, Stratis, Tanoa, Weferlingen, Cam Lao Nam and
Everon; the full list is in [docs/ESCENARIOS.md](docs/ESCENARIOS.md). **Tanoa is the polished one (V6)**, with two
missions:

- **A: Pacific crisis.** US/NATO vs Russia, with tropical gear and only contemporary assets: no 2035 sci-fi and no WWII.
- **B: Colombia and the US vs the narco-insurgency.** The insurgents strike the capital in the first minutes;
  the airfields stay key points. To win, you take every town; if the insurgency is cornered, it has 8 minutes to recover.

**Lingor (new):** mission B also runs on Lingor/Dingor Island (Workshop 718649903), a South American jungle map. It uses all the Tanoa systems, a jungle camo and a 2.5 km view distance. The base mission is generated locally with `python3 tools/vio_port.py build lingor`, and `tools/vio_build.py` then builds `lingor_colombia` on it.

Tanoa features (each is a patch in `tools/vio_patches/` and a lobby parameter you can turn off):

| | |
|---|---|
| **Performance** | Wrecks, dropped weapons and abandoned vehicles are cleaned up, and the AI count has a budget. With `-maxMem=16383` the game stays at about 19 GB instead of 32 GB. |
| **Bases and airfields** | Reforger-style forward bases. Captured airfields rearm and refuel your aircraft and are defended; enemy aircraft sit at the airfields you haven't taken yet. |
| **Capital** | Fewer towns, and a strongly defended capital (Georgetown) with insurgent checkpoints. Victory comes from holding the capital and the airfields. |
| **AI** | The AI drives troops in trucks and dismounts on contact. It counterattacks, runs pincer attacks, and both sides use aircraft. The extra Abrams crew bug is fixed. |
| **Support on request** | Up to 5 simultaneous special ops, paradrops you can jump with, an MQ-9 high-altitude UAV, A-10 gun runs, a "Ghostrider" gunship (30 min respawn if shot down), and gunners that obey "fire at this point". |
| **Arsenal help** | Pick any weapon to see its compatible attachments and the ammo it uses. |
| **Front line** | Towns far from the front are safe rear areas: the AI can neither attack nor capture them, and no garrison AI stays there. The fight stays on the front towns. |
| **Irregular warfare (mission B)** | Undercover insurgents with hidden pistols (terrible aim), lookouts that report you, roadside IEDs with a triggerman, ambushes and car bombs. Killing unarmed civilians costs money. |
| **Opening offensive (mission B)** | About 50 insurgents with technicals attack the capital from three directions. Your capital and airfields start manned and defended. |
| **More AI tools** | Helicopter air assaults (Black Hawk, Chinook, Apache escort), FPV drone operators, ION PMC mercenaries guarding a zone boss, and reinforcements for whoever holds the capital. |
| **Ghostrider gun** | Take the AC-130's guns yourself: 105/40/20 mm, zoom and thermal, from a classic C-130. |
| **Quality of life** | Spanish radio voices (mod), up to 8 special ops you can request, straggler cleanup after a capture, your body removed after respawn, and a hold action to delete empty vehicles. |
| **War replay** | The mission records who held each town. At the end (or anytime, via "Ver historia de la guerra") it replays the whole war on the map in 60 s. `tools/war_replay.py` exports it to HTML or GIF. |

## Requirements

- An Apple Silicon Mac and Arma 3 from Steam (the Mac port runs under eON). Tanoa needs the **Apex** DLC.
- The Workshop items each scenario lists in [docs/ESCENARIOS.md](docs/ESCENARIOS.md): the VIO-BECTI-CW mission for that
  map, plus CBA, CUP and/or RHS and the other mods named in [docs/launch/](docs/launch/). No ACE and no mods with DLLs:
  they don't work on the Mac port.
- Python 3. `vio_build.py` uses only the standard library. The war replay exporter needs Pillow, and porting to other
  terrains (`vio_port.py`) or drawing a map background also needs numpy.

## Quick start

```bash
git clone https://github.com/srjefers/arma3-mserieschips-stories.git && cd arma3-mserieschips-stories
python3 tools/vio_build.py list                                  # scenarios and whether their source is downloaded
python3 tools/vio_build.py --dry-run build tanoa_rhs_otan_ru     # build in work/vio_stage/ and show what would change
python3 tools/vio_build.py build tanoa_rhs_otan_ru               # install into .../GameDocuments/Arma 3/mpmissions
```

**Mod loading.** The Mac port fails silently when a `-mod=` line goes over about 600 characters. Here is the workaround:

1. Make a folder `~/m` with **short symlinks** to the Workshop mod folders (`@cba`, `@rhsu`…). The legend is in
   `docs/launch/LAUNCH_OPTIONS.txt`.
2. Copy the `docs/launch/par/*.txt` files into `~/m`, replacing `<usuario>` with your macOS user name.
3. Put one launch line from `docs/launch/LAUNCH_OPTIONS.txt` in Steam → Arma 3 → Properties → Launch options. For
   example, Tanoa uses `-par=C:/Users/<usuario>/m/p_tropical.txt -maxMem=16383 -maxVRAM=8191`.

**Play.** Go to MULTIPLAYER → Server Browser → Host Server (LAN), pick the map and then the "CW: …" mission. Always host;
single-player ignores the lobby parameters. The most useful parameters are explained in
[docs/ESCENARIOS.md](docs/ESCENARIOS.md), and [docs/GUIA_VIO-BECTI.md](docs/GUIA_VIO-BECTI.md) is a gameplay guide
for BECTI.

**War replay export:**

```bash
python3 tools/war_replay.py list
python3 tools/war_replay.py basemap --world Tanoa        # once: draws the map background from your game files
python3 tools/war_replay.py export --html ~/Desktop/war.html --gif ~/Desktop/war.gif
```

## Layout

```
tools/vio_build.py        builds and installs the scenarios (catalog + patch chain)
tools/vio_catalog.json    scenarios: source mission, lobby defaults, patch list
tools/vio_patches/*.json  patches: new files and anchored inserts/replacements on the original mission
tools/vio_doc_params.md   hand-written lobby parameter guide (merged into docs/ESCENARIOS.md)
tools/war_replay.py       war replay exporter (HTML/GIF)
tools/vio_port.py         ports a CW mission to another terrain (e.g. Everon)
tools/pbo_tool.py, vio_sqm.py, vio_wrp.py, ...   PBO, mission.sqm and terrain readers (standard library)
tools/track.sh, undo.sh   every file installed outside the repo is recorded; undo.sh reverts it
docs/                     generated catalog, launch templates, gameplay guide
```

Nothing ever writes to the game, Steam or Workshop folders. The build reads your Workshop copy and writes only to
`mpmissions` and to the repo's ignored `work/` folder. Each install is recorded in the ignored `install_manifest.tsv`,
and `./undo.sh` reverts it.

## Status

- This is a personal project, tested by one player on one Apple Silicon Mac. Windows has not been tried: the paths are Mac-specific.
- The Tanoa V6 features are new; some are still waiting for a long in-game test.
- Issues and ideas are welcome.

## Resumen en español

Misiones Warfare (CTI) para un jugador contra la IA, para **Arma 3 en Mac con Apple Silicon**. Se basan en VIO-BECTI-CW 2.0.6.

- **Qué hay en el repo:** parches y herramientas, no la misión ni los mods. `tools/vio_build.py` arma la misión desde
  tu suscripción del Workshop y la instala.
- **Tanoa (V6) es la más pulida:**
  - **misión A:** EE.UU./OTAN contra Rusia;
  - **misión B:** Colombia y EE.UU. contra la narcoinsurgencia.
  - Trae bases avanzadas, aeródromos, capital con controles, IA con transporte y tácticas, apoyo aéreo,
    paracaidistas, dron MQ-9 e historia animada de la guerra.
- **Cómo jugar:** el catálogo, las líneas de lanzamiento y los parámetros del lobby están en `docs/ESCENARIOS.md` y
  `docs/launch/`.

## License

MIT (see [LICENSE](LICENSE)) for the original code and docs in this repo. VIO-BECTI, Arma 3 and the mods belong to their
authors; see [NOTICE.md](NOTICE.md).
