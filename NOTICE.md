# Third-party notice

The MIT license in [LICENSE](LICENSE) covers only the **original work in this repository**: the tools, the new mission
scripts (`VIOC_*`) inside the patches, and the documentation.

**This repository does not include, and does not redistribute:**

- **VIO-BECTI / VIO-BECTI-CW** (the base Warfare/CTI mission). It is published on the Steam Workshop and at
  [github.com/dukee02/Arma3_CTI](https://github.com/dukee02/Arma3_CTI) by its authors, who hold its rights. It builds on
  the original BECTI by Benny. You must subscribe to it yourself; `tools/vio_build.py` reads your local Workshop copy
  and applies the patches on your machine.
  - The patch files (`tools/vio_patches/*.json`) quote **short fragments** of the original mission code. Those fragments
    are used only as anchors to locate where each change goes, and they remain the property of their authors.
- **Arma 3**, its DLCs (Apex/Tanoa, …), their terrains and data: © Bohemia Interactive. Map backgrounds derived from game
  files are not included; `tools/war_replay.py basemap` draws them on your machine from your own copy.
- **Mods** named in the docs (CBA, CUP, RHS, LAMBS, JSRS, Colombian Armed Forces RHS, …) belong to their authors and are
  only referenced by name and Workshop ID.

This project is not affiliated with Bohemia Interactive, the VIO-BECTI team or any mod author. If you are one of these
authors and want something changed or removed, please open an issue.
