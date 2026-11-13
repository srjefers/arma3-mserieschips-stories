# Ideas de mods para publicar en el Steam Workshop

Banco de ideas para sacar partes de este proyecto como **mods independientes** (y, aparte, la misión B de Tanoa como
escenario) en el Steam Workshop, con su repositorio propio en GitHub. Sale del análisis del 2026-11-04 al 2026-11-07.
Estado: **nada empaquetado ni publicado**; esto es la lista de trabajo.

## Criterio

Todo lo que hay en `tools/vio_patches/` es código nuestro (SQF con prefijo `VIOC_`), escrito como parches sobre
VIO-BECTI-CW 2.0.6. Nada de eso existe como mod en Steam; lo que sí viene de Steam son la misión base y los mods de
unidades y drones. Para decidir qué puede salir como mod normal se midió cuántas variables internas de BECTI (`cti_*`)
usa cada script nuevo:

- **0 a 3 variables:** se puede empaquetar como mod para cualquier misión con poco trabajo.
- **10 a 60 variables:** vive de los pueblos, los dueños, los fondos y los equipos de BECTI. Su casa es la misión.

---

## 1. Candidatos, en el orden recomendado

| # | Mod | Parches de origen | Líneas | Variables de BECTI | Dependencias | Por qué |
|---|---|---|---|---|---|---|
| 1 | **Drones: cámara post-impacto, marcas de drones aliados y FPV para la IA** | `killcam`, `uav_friendly_marks`, `fpv_ai` | 225 + 92 + 584 | 1, 0 y 3 | Ninguna obligatoria. Opcionales: FPV Drone Crocus (ArmaFPV), Drongos Drone Tweaks y CL AI Drone Warfare para que la IA lance | Es donde hay más público (FPV Drone Crocus: 159.353 suscriptores) y no existe ninguna cámara post-impacto en Steam |
| 2 | **Órdenes de fuego** | `fire_orders` | 1.018 | 3 | Solo vanilla | Único: tu artillero IA dispara a un punto o a lo que miras, y la artillería del grupo con munición real. Drongos Artillery (48.247) cubre solo artillería |
| 3 | **Cañón del Ghostrider** | `VIOC_ghostrider_gun.sqf`, dentro de `air_support` | parte de 2.821 | 19 en total, casi todas en el panel de pedido y no en el cañón | C-130J de RHS o CUP | Los AC-130 de Steam suman más de 150.000 suscriptores (USAF_AC130_BETA 140.134, STmod_AC130J 10.165). Hay que separar el cañón del sistema de pedidos |
| 4 | **Misión B de Tanoa como escenario** | todo el catálogo `tanoa_colombia` | | | VIO-BECTI-CW Tanoa, CBA, CUP, RHS y los mods de la línea 12 | El producto completo y lo que más se ha jugado. Requiere el permiso de VIO (ver bloqueos) |

### Segunda ola, si los primeros funcionan

| Mod | Parche | Líneas | Variables de BECTI | Nota |
|---|---|---|---|---|
| Civiles en los pueblos | `civ_people` | 396 | 6 (lista de pueblos) | Con las localidades del mapa en vez de los pueblos de BECTI. Compite con Simple Civilian Behaviour (34.449) y RCiv (19.711) |
| Rastreadores | `trackers` | 398 | 12 | Hay que definir "territorio enemigo" sin pueblos (por ejemplo, cerca de grupos enemigos) |
| Vehículos atascados de la IA | `perf_stuck` | 135 | 6 | Pequeño; hay muchos limpiadores en Steam, poco valor por separado |

## 2. Lo que no se publica por separado

Operaciones especiales y paracaidistas (`ai_specops`, `specops_*`, `para_*`, `heli_join`), apoyo aéreo y dron a pedido
(`air_support` salvo el cañón, `uav_request`), asalto aéreo (`air_assault`), frente y retaguardia (`front_line*`),
capital (`towns_capital`, `capital_reinforce`), bases avanzadas y aeródromos (`forward_bases`, `airfields`), bloqueos y
campamentos (`enemy_roadblocks`, `enemy_camps`), mercenarios (`mercenaries`, `merc_ops`), guerra irregular
(`irregular_warfare`), historia de la guerra (`war_replay`) y las reglas de la misión B. Usan entre 10 y 60 variables de
BECTI. Van dentro del escenario (candidato 4) y ya están publicados en GitHub como parches.

## 3. Bloqueos a resolver antes de subir nada

1. **Permiso de VIO para el escenario.** Su repositorio (github.com/dukee02/Arma3_CTI, última actualización
   2026-04-03) no tiene licencia y la página del Workshop (2974799271) no dice nada de reutilizar. Ellos construyen
   sobre el BECTI de Benny, pero sus añadidos son suyos. Pedir permiso por su Discord antes de publicar una misión
   derivada. Los tres mods no tienen este problema: son código nuestro con licencia MIT.
2. **Empaquetar como mod.** Cada mod necesita un PBO con `config.cpp` (`CfgPatches` y `CfgFunctions` con `postInit`);
   los parámetros del lobby pasan a ajustes de CBA (`CBA_settings_fnc_init`) o a variables de misión. `tools/pbo_tool.py`
   solo lee y parchea PBO: añadirle un comando `pack` que cree uno desde una carpeta. SQF en ASCII, como siempre. Sin DLL
   (CBA no tiene), así que seguimos dentro de las reglas del Mac.
3. **Firma.** La firma `.bisign` se hace con DSSignFile (Arma 3 Tools, solo Windows). Sin firma el mod funciona en
   partidas hospedadas y LAN, pero no entra en servidores que verifican firmas. Decidir si importa.
4. **Subir desde el Mac.** El Publisher de Arma 3 Tools es solo Windows. Dos caminos:
   - publicar el escenario desde el editor Eden dentro del juego (sin probar en el port);
   - SteamCMD, que existe para macOS y sube ítems de Arma 3 (appid 107410) con `workshop_build_item` y un archivo VDF
     propio. Ese VDF lo escribimos nosotros en el repo; **no es ninguno de los `.vdf` de Steam**, que no se tocan. El
     inicio de sesión lo hace el dueño. Referencia: gist de maca134,
     https://gist.github.com/maca134/9bbe75e3096a94913df69d906926fa28
5. **Probar en el juego antes de publicar.** Varios parches siguen sin probarse. Solo se publica lo ya jugado.

## 4. Pasos por mod

1. Nombre y repositorio propio en GitHub (uno por ítem del Workshop, con README, licencia MIT y capturas), para que la
   página del Workshop enlace al código y el usuario no tenga que entender el sistema de parches.
2. Extraer el script del parche y quitar las dependencias de BECTI (bando del jugador con `side player`, equipos con
   `allGroups`, parámetros por CBA).
3. `config.cpp`, PBO con `pbo_tool.py pack`, carpeta `@mod` con `mod.cpp`.
4. Probar en LAN con la misión B de Tanoa y con una misión vanilla sin BECTI.
5. Subir con SteamCMD (el dueño). Página del Workshop: qué hace, mods opcionales, "sin DLL, funciona en el port de Mac",
   enlace a GitHub.
6. Ir anotando aquí qué quedó publicado, con su ID.

## 5. Referencias del Workshop

| Ítem | ID | Para qué |
|---|---|---|
| FPV Drone Crocus (ArmaFPV) | 3045129955 | dependencia opcional del mod 1; público objetivo |
| Drongos Drone Tweaks | 3456575967 | la IA lanza los FPV (mod 1) |
| USAF_AC130_BETA | 2226368165 | referencia de demanda del mod 3 |
| STmod_AC130J | 3686190970 | referencia de demanda del mod 3 |
| Fire Support Plus | 2699465073 | lo más parecido a pedidos de apoyo; no se compite con eso |
| Drongos Artillery | 1675485070 | lo más parecido al mod 2 |
| Simple Civilian Behaviour | 3529745801 | competencia de los civiles (segunda ola) |
| VIO-BECTI-CW Tanoa V2.0.6 | 2974799271 | misión base del candidato 4 |
