# CLAUDE.md

Single-player Warfare (CTI) missions for Arma 3 on Apple Silicon Macs (official Mac port 2.22, Windows exe under eON),
built as **patches over VIO-BECTI-CW 2.0.6**. Read [README.md](README.md) for the overview and
[NOTICE.md](NOTICE.md) for what may and may not be committed.

## Language

The owner works in **Spanish**: answer in Spanish. Docs and code comments are in Spanish, while README, NOTICE and
this file are in English. In `.sqf` files use **ASCII only**: Spanish without accents, `anio`, `duenio`.

## Hard rules (machine safety)

- No `sudo`. Never modify game, Steam or Workshop files, and never edit Steam `.vdf` files.
- Workshop subscriptions are done by the owner: give grouped links and wait for confirmation. Before recommending a mod,
  check its page (title, required items, last update, required DLC, not removed).
- Exclude ACE and any mod with DLLs; RHS is allowed. After each download run
  `find <folder> -iname "*.dll"` and report hits before using the mod. Ask before downloading anything over 1 GB.
- Anything created outside the repo (symlinks in `~/m` or `~/ArmaMods`, copies, mission folders) goes through
  `tools/track.sh` (`track_copy`, `track_symlink`, `untrack_remove`). It is recorded in `install_manifest.tsv`, so
  `./undo.sh` can revert it.
- Log every change in `INSTALL_LOG.md` and keep open work in `PENDIENTES.md`. Use the real time from `date`. Both are
  **local only** (gitignored).
- Never alter saved games or the Arma profile without a backup and the owner's OK.
- The Mac port has no `.rpt`. To diagnose, read `~/Library/Application Support/com.vpltd.Arma3/eon.txt`, which is
  overwritten each launch, and `tools/arma_memlog.sh` logs. Give the concrete cause before proposing changes.

## Building missions

- `tools/vio_catalog.json` lists the scenarios: source Workshop mission, lobby param defaults and an ordered
  `patches` list. `tools/vio_patches/<name>.json` holds the steps: `new_file`, `append`, `replace`, `insert_before`,
  `insert_after`.
  - **Each anchor must appear exactly once** in the file *at its point in the chain*: later patches see earlier ones'
    text.
  - Anchor on original BECTI lines when possible.
  - Patches only insert into shared files. Their logic goes in new `VIOC_*.sqf` files.
- Edit the catalog at the text level and verify with `json.loads(new) == expected`. Back it up first, in `work/`.
- Always simulate first: `PYTHONDONTWRITEBYTECODE=1 python3 tools/vio_build.py --dry-run build all`. The expected
  result is all scenarios, 0 errors, and only the intended ones "actualizaría".
  - Stages go to `work/vio_stage/`.
  - To test without touching anything, set `VIO_STAGE_DIR` and point `vio_build.PATCH_DIR` at a temp dir.
- **Install only when the owner says "aplica"**, and only with Arma closed:
  `ps axo comm | grep -i -E "arma3|Arma3Retail|ArmA3"` must be empty.
  - Run `vio_build.py build <ids>`.
  - An installed folder that changed since it was recorded is refused (hash check).
  - The folder name stays the same, so saves survive.
- After catalog, doc or launch changes, run `python3 tools/vio_build.py doc`. It rewrites the local `ESCENARIOS.md`
  and the public, sanitized `docs/ESCENARIOS.md` and `docs/launch/`.
- Lobby parameter docs are hand-written in `tools/vio_doc_params.md` (Tanoa V6 and mission B sections).

## SQF conventions

- Everything new is prefixed `VIOC_`. Params go in `RSC/Parameters.hpp`; read them with
  `missionNamespace getVariable ["VIOC_X", default]`.
- The target is a hosted game where `isServer && hasInterface` are both true; it must still work on a dedicated server.
- `.fsm` code lives inside strings: double quotes become `""`, and lines end in `\n`.
- Things that have bitten before:
  - SQF names are case-insensitive, so `_w` and `_W` are the same variable.
  - `forEach (+array)` is a deep copy, so writes to the copy are lost.
  - Use `isNil {}` for atomic server sections.
  - Use `remoteExecCall` with `remoteExecutedOwner` checks.
- Complex patches (end-of-game flow, AI orders, spawning) get an independent adversarial review before "aplica".

## Performance facts

- eON reports about 36 GB of RAM to the engine, so the default memory budget lands near 29 GB. Launch lines use
  `-maxMem=16383`; that was verified in game at about 19 GB.
- The Mac port silently breaks `-mod=` lines over about 600 characters. Use short symlinks in `~/m` and `-par=` files
  (`par/`, copied to `~/m`).

## Privacy, before any commit

- Never commit the local files listed in `.gitignore`: logs, the manifest, `par/`, `LAUNCH_OPTIONS.txt`, `work/`,
  `research/`, `backups/`.
- Never commit anything with the owner's macOS user path or machine layout. Check with
  `git grep -n "$(basename "$HOME")"`, which must print nothing.
- Never commit game-derived assets: map PNGs, PBOs, profiles.
