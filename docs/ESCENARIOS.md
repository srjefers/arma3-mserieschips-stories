# Escenarios configurados

Generado por `tools/vio_build.py doc` desde `tools/vio_catalog.json` y `LAUNCH_OPTIONS.txt`.

Las rutas `C:/Users/<usuario>/m/...` son la carpeta `~/m` vista desde el juego (el puerto de Mac la ve como `C:/Users/<tu usuario del Mac>`): cambia `<usuario>` por tu usuario. Plantillas en `docs/launch/`.

## Cómo lanzar el juego (líneas de Steam)

En **Steam → Arma 3 → Propiedades → General → Opciones de lanzamiento** pega **una** línea, según lo que vayas a jugar. Después de cambiarla, cierra y vuelve a abrir el juego. Para jugar sin mods, borra el texto. Las mismas líneas están en `docs/launch/LAUNCH_OPTIONS.txt`.

Las rutas usan nombres cortos (carpeta ~/m, leyenda al final): el Mac no carga bien los mods si la línea es muy larga (con 912 caracteres fallaba: sin mapas de CUP y soldados sin equipo; con 592 funcionaba). Mantener cada línea por debajo de ~600 caracteres. Las líneas 6 y 10 ("-par=") leen la lista de mods de un archivo en ~/m (copia en la carpeta par/ del proyecto): así la línea de Steam es corta y no hay límite (-par probado en el Mac el 2026-10-13). Los Creator DLC se cargan con el nombre de su carpeta: GM, vn, CSLA, WS, SPE, RF, EF. Toda línea con JSRS lleva también WS: JSRS declara el mapa Sefrou-Ramal y sin WS el juego avisa "No entry ...CfgWorlds/sefrouramal.description".

**1V) SELVA 2026 (569 caracteres)**

CUP, RHS y los mods de la antigua línea 1, más S.O.G. Prairie Fire. SOLO para "CW: Selva 2026" en Cam Lao Nam: con S.O.G. y CUP cargados, cualquier misión CW arranca con los pueblos repartidos 50:50 (error del autor).

```
-mod=vn;WS;C:/Users/<usuario>/m/@cba;C:/Users/<usuario>/m/@cupc;C:/Users/<usuario>/m/@cupm;C:/Users/<usuario>/m/@cupw;C:/Users/<usuario>/m/@cupu;C:/Users/<usuario>/m/@cupv;C:/Users/<usuario>/m/@rhsr;C:/Users/<usuario>/m/@rhsu;C:/Users/<usuario>/m/@rhsg;C:/Users/<usuario>/m/@jsrs;C:/Users/<usuario>/m/@fpv;C:/Users/<usuario>/m/@mav;C:/Users/<usuario>/m/@dro;C:/Users/<usuario>/m/@cld;C:/Users/<usuario>/m/@inv;C:/Users/<usuario>/m/@war;C:/Users/<usuario>/m/@pir;C:/Users/<usuario>/m/@wbk;C:/Users/<usuario>/m/@ser;C:/Users/<usuario>/m/@dhr;C:/Users/<usuario>/m/@pdc;C:/Users/<usuario>/m/@fal
```

**2) UKRAINE WAR (386 caracteres)**

Un jugador > Escenarios > "Ukraine war". RHS + el mapa Krayina y sus objetos, audio y sangre, más granadas SER, TrueColor y Blastcore. Sin CUP (no lo necesita) y sin PiR (la misión tiene su propio sistema de reaparición).

```
-mod=WS;C:/Users/<usuario>/m/@cba;C:/Users/<usuario>/m/@rhsr;C:/Users/<usuario>/m/@rhsu;C:/Users/<usuario>/m/@rhst;C:/Users/<usuario>/m/@hag;C:/Users/<usuario>/m/@kra;C:/Users/<usuario>/m/@sua;C:/Users/<usuario>/m/@arm;C:/Users/<usuario>/m/@jsrs;C:/Users/<usuario>/m/@wbk;C:/Users/<usuario>/m/@ser;C:/Users/<usuario>/m/@dhr;C:/Users/<usuario>/m/@sgr;C:/Users/<usuario>/m/@tco;C:/Users/<usuario>/m/@cob
```

**2b) UKRAINE WAR CON DRONES EXTRA (486 caracteres)**

Igual que la 2, más los mods de drones. La misión ya trae sus propios drones (tu cuadricóptero con granada y carga explosiva; drones suicidas, bombarderos y el Pchela de reconocimiento rusos). Con esta línea además tienes el FPV y el Mavic en el arsenal, y la IA (de los dos bandos) puede llevar mochilas FPV. Combinación sin probar: más drones y más difícil.

```
-mod=WS;C:/Users/<usuario>/m/@cba;C:/Users/<usuario>/m/@rhsr;C:/Users/<usuario>/m/@rhsu;C:/Users/<usuario>/m/@rhst;C:/Users/<usuario>/m/@hag;C:/Users/<usuario>/m/@kra;C:/Users/<usuario>/m/@sua;C:/Users/<usuario>/m/@arm;C:/Users/<usuario>/m/@jsrs;C:/Users/<usuario>/m/@fpv;C:/Users/<usuario>/m/@mav;C:/Users/<usuario>/m/@dro;C:/Users/<usuario>/m/@cld;C:/Users/<usuario>/m/@wbk;C:/Users/<usuario>/m/@ser;C:/Users/<usuario>/m/@dhr;C:/Users/<usuario>/m/@sgr;C:/Users/<usuario>/m/@tco;C:/Users/<usuario>/m/@cob
```

**5) ANTISTASI (438 caracteres)**

MULTIPLAYER > Host Server (LAN) > mapa > Antistasi Ultimate. Tú diriges la guerrilla. CUP y sus mapas, Isla Pera, Antistasi Ultimate, audio y sangre, más granadas SER, TrueColor, HLS y Blastcore. Sin RHS (Antistasi pide CUP o RHS, no los dos) y sin PiR (Antistasi no lo admite). Con los Creator DLC, usa la 9.

```
-mod=WS;C:/Users/<usuario>/m/@cba;C:/Users/<usuario>/m/@cupc;C:/Users/<usuario>/m/@cupm;C:/Users/<usuario>/m/@cupw;C:/Users/<usuario>/m/@cupu;C:/Users/<usuario>/m/@cupv;C:/Users/<usuario>/m/@got;C:/Users/<usuario>/m/@ant;C:/Users/<usuario>/m/@jsrs;C:/Users/<usuario>/m/@inv;C:/Users/<usuario>/m/@wbk;C:/Users/<usuario>/m/@ser;C:/Users/<usuario>/m/@dhr;C:/Users/<usuario>/m/@sgr;C:/Users/<usuario>/m/@tco;C:/Users/<usuario>/m/@hls;C:/Users/<usuario>/m/@cob
```

**6) CW CON TODO (archivo -par)**

Las misiones CW, también las de Weferlingen (Global Mobilization), con los vehículos de Western Sahara, Reaction Forces y Expeditionary Forces. CUP, RHS, JSRS, drones, inventario 3D, Wardrobe, PiR y sangre, mapa Fallujah, Blackthorn, UK y QAV (@nue), IA LAMBS, segunda arma KJW (tecla 4), inhibidor Sania, granadas SER (con su parche PiR), TrueColor (Ctrl+Alt+C), iluminación HLS, Blastcore y los mapas CWA (Everon, Nogova, Kolgujev, Malden 1985). Lista en ~/m/p_cw.txt.

```
-par=C:/Users/<usuario>/m/p_cw.txt
```

**7) CREATOR DLC (435 caracteres)**

Campañas y escenarios oficiales de los 7 Creator DLC y misiones del Workshop en sus mapas (DRO, Impasse, HWS, Desert Ocean...). Con CUP y RHS para las misiones que los usan, audio, sangre y efectos; sin PiR.

```
-mod=GM;vn;CSLA;WS;SPE;RF;EF;C:/Users/<usuario>/m/@cba;C:/Users/<usuario>/m/@cupw;C:/Users/<usuario>/m/@cupu;C:/Users/<usuario>/m/@cupv;C:/Users/<usuario>/m/@rhsr;C:/Users/<usuario>/m/@rhsu;C:/Users/<usuario>/m/@rhsg;C:/Users/<usuario>/m/@jsrs;C:/Users/<usuario>/m/@inv;C:/Users/<usuario>/m/@wbk;C:/Users/<usuario>/m/@ser;C:/Users/<usuario>/m/@dhr;C:/Users/<usuario>/m/@sgr;C:/Users/<usuario>/m/@tco;C:/Users/<usuario>/m/@hls;C:/Users/<usuario>/m/@cob
```

**8) VIETNAM (361 caracteres)**

S.O.G. Prairie Fire, "CW: Vietnam 1968" en Cam Lao Nam (los dos bandos), Insurgency Vietnam y DRO Cam Lao Nam. Sin CUP ni RHS (con S.O.G. cargado la misión CW fuerza pueblos 50:50 si hay CUP o RHS).

```
-mod=vn;WS;C:/Users/<usuario>/m/@cba;C:/Users/<usuario>/m/@jsrs;C:/Users/<usuario>/m/@inv;C:/Users/<usuario>/m/@war;C:/Users/<usuario>/m/@pir;C:/Users/<usuario>/m/@wbk;C:/Users/<usuario>/m/@ser;C:/Users/<usuario>/m/@dhr;C:/Users/<usuario>/m/@pdc;C:/Users/<usuario>/m/@sgr;C:/Users/<usuario>/m/@psc;C:/Users/<usuario>/m/@tco;C:/Users/<usuario>/m/@hls;C:/Users/<usuario>/m/@cob
```

**9) ANTISTASI CON CREATOR DLC (455 caracteres)**

Antistasi Ultimate también en Weferlingen, Cam Lao Nam, Khe Sanh, Gabreta y Sefrou-Ramal. Las facciones se eligen a mano al empezar (lista en work/vio_cdlc/solo_modes.md).

```
-mod=GM;vn;CSLA;WS;RF;EF;C:/Users/<usuario>/m/@cba;C:/Users/<usuario>/m/@cupc;C:/Users/<usuario>/m/@cupm;C:/Users/<usuario>/m/@cupw;C:/Users/<usuario>/m/@cupu;C:/Users/<usuario>/m/@cupv;C:/Users/<usuario>/m/@got;C:/Users/<usuario>/m/@ant;C:/Users/<usuario>/m/@jsrs;C:/Users/<usuario>/m/@inv;C:/Users/<usuario>/m/@wbk;C:/Users/<usuario>/m/@ser;C:/Users/<usuario>/m/@dhr;C:/Users/<usuario>/m/@sgr;C:/Users/<usuario>/m/@tco;C:/Users/<usuario>/m/@hls;C:/Users/<usuario>/m/@cob
```

**10) TROPICAL, TANOA V6 (archivo -par, con tope de memoria)**

Misiones CW de Tanoa. Como la 6 pero sin GM, sin los mapas de CUP, CWA ni Fallujah (no hacen falta en Tanoa y ocupan memoria). -maxMem=16383 le pide al motor no pasar de 16 GB (sin esto se da hasta el 80 % de la RAM, unos 28.6 GB en este Mac); -maxVRAM=8191 limita las texturas, aunque puede que el motor lo ignore. Por probar (2026-10-16): mide con tools/arma_memlog.sh. Lista en ~/m/p_tropical.txt. Desde el 2026-10-16 también trae Enhanced Movement Rework (saltar y trepar), WBK Immersive Animations, DUI Squad Radar (radar de tu escuadra) y Advanced Towing (remolcar vehículos). ACSTG y el ejército colombiano todavía no.

```
-par=C:/Users/<usuario>/m/p_tropical.txt -maxMem=16383 -maxVRAM=8191
```

**11) EDITOR TROPICAL (archivo -par)**

Para el Editor (Eden) con mapas tropicales (Tanoa, Isla Pera, Cam Lao Nam) y todas las facciones: CUP, RHS, S.O.G., el ejército colombiano, 3den Enhanced (herramientas del Editor), LAMBS, ACSTG (la IA no ve a través de la hierba), movimiento, animaciones, radar de escuadra, remolque, audio y efectos. No es para las misiones CW: con S.O.G. cargado, los pueblos salen 50:50. Lista en ~/m/p_eden_tropical.txt.

```
-par=C:/Users/<usuario>/m/p_eden_tropical.txt -maxMem=16383
```

**12) MISION B, COLOMBIA CONTRA EL NARCO (archivo -par, con tope de memoria)**

"CW: Colombia y EE.UU. contra la narcoinsurgencia (Tanoa)". La línea 10 más el ejército colombiano (@col). Solo para esta misión: @col cambia piezas internas del juego (los obuses dejan de contar como armas fijas), así que no se usa en las demás. Lista en ~/m/p_tropical_col.txt.

```
-par=C:/Users/<usuario>/m/p_tropical_col.txt -maxMem=16383 -maxVRAM=8191
```

**LEYENDA de nombres cortos (~/m/@corto apunta a la misma carpeta que ~/ArmaMods/@largo)**

| Nombre corto | Mod |
|---|---|
| `@cba` | CBA_A3 |
| `@cupc` | CUP_Terrains_Core |
| `@cupm` | CUP_Terrains_Maps |
| `@cupw` | CUP_Weapons |
| `@cupu` | CUP_Units |
| `@cupv` | CUP_Vehicles |
| `@rhsr` | RHSAFRF |
| `@rhsu` | RHSUSAF |
| `@rhsg` | RHSGREF |
| `@rhst` | RHSTERRACORE |
| `@jsrs` | JSRS_SOUNDMOD_2025 |
| `@fpv` | ArmaFPV |
| `@mav` | Mavic3_Improved |
| `@dro` | Drongos_Drone_Tweaks |
| `@cld` | CL_AI_Drone_Warfare |
| `@inv` | Inventory_Preview |
| `@war` | Wardrobe |
| `@pir` | PiR |
| `@wbk` | WBK_Simple_Blood |
| `@ser` | SER_Impacts |
| `@dhr` | Death_Hit_Reactions |
| `@pdc` | PiR_DHR_Compat |
| `@fal` | Fallujah_2 |
| `@hag` | HAG_Objects |
| `@kra` | Krayina |
| `@sua` | Squad_Ukraine |
| `@arm` | Simple_Armbands |
| `@got` | Global_Ops_Terrains |
| `@ant` | Antistasi_Ultimate |
| `@nue` | Nuevos_TRF_QAV |
| `@lmb` | LAMBS_Danger |
| `@kjw` | KJW_TwoPrimaryWeapons |
| `@san` | Sania_Volnorez_EW |
| `@sgr` | SER_Grenades |
| `@psc` | PiR_SER_Compat |
| `@tco` | TrueColor |
| `@hls` | HLS_Lighting |
| `@cob` | Blastcore_CoB |
| `@cwa` | CUP_Terrains_CWA |
| `@em` | Enhanced_Movement |
| `@emr` | Enhanced_Movement_Rework |
| `@wia` | WBK_Immersive_Animations |
| `@dui` | DUI_Squad_Radar |
| `@tow` | Advanced_Towing |
| `@3de` | 3den_Enhanced |
| `@acs` | ACSTG |
| `@col` | Colombian_Armed_Forces_RHS |
| `GM` | Global Mobilization |
| `vn` | S.O.G. Prairie Fire |
| `CSLA` | CSLA Iron Curtain |
| `WS` | Western Sahara |
| `SPE` | Spearhead 1944 |
| `RF` | Reaction Forces |
| `EF` | Expeditionary Forces |

## Parámetros útiles del lobby (misiones CW)

Se cambian en **MULTIPLAYER → Host Server → (eliges la misión) → PARAMETERS**, en la pantalla de elegir puesto. Solo funcionan si hospedas: en "Un jugador" la misión los ignora. Los valores de la columna "Por defecto" son los de nuestras copias configuradas; cada partida nueva vuelve a ellos.

| Parámetro (como sale en el lobby) | Por defecto | Para qué sirve y cuándo cambiarlo |
|---|---|---|
| BASE: Start-up Placement | 6 KM | Distancia mínima entre las dos bases al empezar. En las misiones "frente" no decide nada mientras "VIOC: Bases cerca del frente" esté en "Si". Sin esa opción, en Malden conviene "Use Default": tu base sale en el norte y tu primer pueblo enemigo queda a 3.2 km. Bajarlo a 4 KM no acerca tu lado del frente, solo la base enemiga. |
| VIOC: Bases cerca del frente | Si: frente a 1.5-3 km | Solo en las misiones "frente" (TOWNS: 50% East, 50% West). Elige puntos de arranque en los que el primer pueblo enemigo de cada base queda a 1.5-3 km y reparte los pueblos mitad y mitad entre las dos bases. "Mas variedad" = 1.2-3.5 km, con más disposiciones posibles; "No" = sorteo original. Con una partida guardada no cambia nada hasta empezar con PERSIST en "Disabled" o "Reset". |
| BASE: Start Near towns | 2 KM | Distancia máxima entre el punto de inicio de una base y el pueblo más cercano. Más bajo = la base arranca pegada a un pueblo. En las misiones "frente" déjalo en 2 KM: con 1 KM, en Malden y Livonia no queda ninguna pareja de bases que cumpla. |
| BASE: FOB Limit | 6 | Cuántos FOB (bases avanzadas) puede construir cada bando. Un FOB cerca del frente sirve para reaparecer ahí. |
| VIOC: Estilo de bases y estructuras | Nuevo (estilo Reforger) | Cambia el aspecto de lo que construye la misión. Este (soviético/ruso): caseta de guardia como HQ, cuartel de ladrillo, garajes, radar móvil, torre de control. Oeste (OTAN): tienda de mando, Cargo HQ, red de camuflaje, radar de cúpula, torre Cargo. El FOB es una tienda médica con las puertas abiertas: entras para abrir el equipo y te curas dentro. Depósito y campamento de pueblo de sacos terreros; el campamento ya no se puede destruir. Agrega 19 fortificaciones al menú de construcción (categorías "Fortification" y "Camo"). Precios, tiempos y resistencia no cambian. "Original" = los edificios de Arma 2 de siempre. Con CUP, el depósito de munición conserva el edificio de antes, que rearma, repara y reposta gratis a 15 m. Si cambias de estilo con una partida guardada, la base vuelve con los modelos del estilo elegido, pero los FOB y las fortificaciones guardados no vuelven. |
| TOWNS: Starting Mode | según la misión | "Resistance" = todos los pueblos empiezan en manos de la guerrilla (misiones "pueblos con guerrilla"). "50% East, 50% West" = el mapa empieza repartido mitad y mitad (misiones "frente"). Los modos "Coop" ponen a los jugadores juntos en un bando. |
| TOWNS: Independent / TOWNS: Occupation | Normal | Dureza de los defensores de los pueblos (guerrilla / ocupación). |
| TOWNS: Amount | Full | Cuántos pueblos hay en juego. "Small" o "Medium" = partidas más cortas. |
| TOWNS: Vehicle Lock | Unlocked | Si puedes usar los vehículos de los pueblos. En nuestras copias están desbloqueados. |
| TOWNS: Max Time before town units despawn | 5 min | Cuánto tardan en desaparecer los defensores de un pueblo cuando te alejas. |
| TOWNS: Purchase Units | Unarmed cars only | Qué se puede comprar en el depósito de tus pueblos. "Cars, basic infantry and support trucks" = también infantería básica y camiones, útil para reforzar el frente sin volver a la base. |
| AI: Skill (all AI units) | 30% Novice | Habilidad de **toda** la IA, de los dos bandos. Déjalo en 30%: desde 40% la IA de los dos bandos deja de comprar al 1% del precio y sus escuadras quedan casi vacías. Para mejorar solo a tus aliados usa "VIOC: Habilidad de la IA de tu bando". |
| VIOC: Operaciones especiales de la IA (paracaidistas y fuerzas especiales) | Si, los dos bandos | Cada bando con IA puede lanzar, si le alcanza el dinero, una operación especial contra un pueblo enemigo del frente (o para reforzar uno propio atacado): paracaidistas desde avión o helicóptero (82.ª Aerotransportada, VDV rusos, paracaidistas de la CDF, Fallschirmjäger de 1985), un equipo de fuerzas especiales en helicóptero (Delta, MARSOC, Force Recon, operadores navales estilo SEAL, Spetsnaz del GRU, Spetsnaz naval, SSO ucranianas, Legión Internacional, saboteadores del ChDKZ; Viper y Spetsnaz en la clásica) o, de noche, una incursión a pie. Llevan supresor y, de noche, visión nocturna. Toman el pueblo, lo mantienen 15 min y se retiran. Paga el comandante IA (unos 7 000-12 000, sin bajar de 5000); si el comandante eres tú, paga el equipo IA más rico de tu bando y tu dinero no se toca. Avisos en el chat y en pantalla si el enemigo salta cerca de tus pueblos. "Solo el bando enemigo (IA)" = solo el bando sin jugadores; "No" = original. No está en Vietnam 1968. |
| VIOC: Operaciones especiales, una como maximo cada (por bando) | 20 min | Separación mínima entre operaciones de un mismo bando (10, 15, 20 o 30 min); la primera llega entre el 60 % y el 100 % de ese tiempo. Nunca hay dos a la vez por bando ni más de 16 soldados especiales vivos. |
| VIOC: Fortificaciones | Si | Cada estática de pueblo tiene su nido, orientado hacia donde dispara: sacos terreros abiertos por detrás para ametralladoras y antitanques (a veces con red de camuflaje, o dentro de un búnker pequeño), y anillos de barreras H para antiaéreos y cañones. Las defensas de base con dotación automática reciben lo mismo; las que compra la IA miran hacia afuera de su base. Verde en mapas boscosos (también Everon, Weferlingen y Cam Lao Nam) y arena en el resto. Nada tapa la línea de tiro ni atraviesa casas o rocas, y todo desaparece junto con su estática. Si la IA dirige un bando y ve venir un ataque a un pueblo suyo o a su base, paga de su dinero (sin bajar de 5000) entre 1 y 3 nidos extra con tirador, del lado del enemigo; nunca a menos de 250 m de ti ni a tu vista, y se retiran 3 min después de la calma. Los sacos no se pueden quitar con la herramienta de quitar defensas. En Vietnam 1968 solo hay nidos en la base. "No (original)" = como antes. |
| VIOC: Armamento de la IA (armas segun rol, nacion y epoca; escuadras con sus especialistas) | Variado (recomendado) | Cada soldado IA nuevo (equipos IA de los dos bandos, guerrilla y guarniciones de los pueblos, tripulaciones, artilleros y también los soldados que compras tú; nunca un jugador) recibe un arma de su ejército, su época y su función: EE.UU. M4A1, HK416, M27, M249, M240, Mk48, M110, M2010; Rusia AK-74M, AK-12, RPK, Pecheneg, SVD, T-5000; Ucrania AK-74, Fort, Bren 2, Minimi, MG3; guerrilla AKM, SKS, Mosin, FAL, PKM; en 1985 M16A2, M60, AK-74, SVD (sin miras modernas). Con su munición y el primer cargador puesto; a veces una mira de su ejército. Los antitanque y antiaéreos cambian de lanzador dentro de su tipo (los guiados como Javelin o Metis no se tocan); a veces cambian pistola y casco. Una parte conserva el arma de fábrica. No toca uniformes, chalecos, mochilas, fuerzas especiales ni escopetas; si algo no cabe, el soldado se queda con lo que traía. Además, al comprar infantería los equipos IA prefieren el médico, ametrallador, antitanque o tirador que les falta, y ya no pierden turnos eligiendo unidades que no pueden pagar (mismas unidades, niveles y precios del autor). "Original" = como antes. |
| VIOC: Taller de armas | Si | Acción "TALLER: Accesorios de armas" donde sale "MENU: Equipment" (cuartel, camión de munición, FOB o campamento) y botón "Taller de armas" abajo en el menú de equipo. Abre el Arsenal con tu soldado en 3D, solo con tus armas: eliges mira, boca, lateral y bípode entre los accesorios que vende tu tienda y que le quedan a esa arma. Arriba ves el costo y un botón "Cancelar (sin cambios)". Al salir con Esc se cobra el precio de tienda de cada accesorio nuevo (lo que ya llevabas no cuesta, y lo que tengas en la mochila se monta gratis); lo que quitas va a tu mochila si cabe y el resto de tu equipo no cambia. Si no te alcanza, se deshace todo. Mientras estás en el taller no te pueden herir. La primera vez en cada partida tarda unos segundos en cargar. El segundo fusil de KJW se cambia primero con la tecla 4. Además, la pestaña de accesorios del menú de equipo solo muestra los que le quedan a las armas de la unidad que editas, ordenados por tipo (miras, bocas, laterales, bípodes). "No" = como antes. |
| VIOC: Habilidad de la IA de tu bando (el enemigo no cambia) | Mejorada (recomendado) | Sube la detección, reacción, valor y recarga de la IA de tu bando, y un poco su puntería. El enemigo queda igual. Si tus aliados quedan demasiado fuertes, baja a "Un poco mejor"; "Igual que el enemigo" = original. |
| VIOC: La IA de tu bando nunca huye | Si (recomendado) | Las escuadras IA de tu bando no salen corriendo, igual que los defensores de los pueblos. "No" = original. |
| VIOC: Refuerzos de la IA en el frente | Si | Cuando un equipo de IA está a más de 1.5 km de su fábrica, los soldados y vehículos de tierra que compra aparecen en el punto propio seguro más cercano al líder (pueblo, campamento, FOB o estructura; sin enemigos a 400 m y sin mar de por medio). Mismo precio. Los líderes que mueren reaparecen cerca del frente. Aviones y lanchas siguen saliendo de su fábrica. Vale para los dos bandos. "No (original)" = todo sale de la base. |
| VIOC: Vehiculos QAV en las fabricas del Oeste | Si (EE.UU. u OTAN) | Solo con la carpeta @nue cargada (línea 6 o 10). Suma al menú de compra del Oeste el AMV-7 Marshall APC, MGS y MGS-UP y el AMV-7A Guardian (antiaéreo con radar) en la fábrica ligera, y el MV-35 Phantom (transporte de 20 asientos) en la aérea, al nivel de su equivalente (Stryker, M1128, MV-22). Son vehículos ficticios de 2035: en las misiones históricas (Chernarus 2009, Donbás 2015) ponlo en "No". "Si, tambien si el Oeste es Ucrania" los suma en las misiones de Ucrania. La IA no los compra. |
| VIOC: Vehiculos de Arma 3 y sus DLC | Si | OTAN al Oeste y CSAT al Este en las fábricas (Hunter, Prowler, Marshall, Slammer, Panther, Ghost Hawk, Blackfoot, Black Wasp, Blackfish... / Ifrit, Qilin, Marid, Varsuk, Angara, Kajman, Taru, Shikra, Xi'an...), al nivel y precio de su equivalente; verde en mapas boscosos y arena en el resto. "Si, y ademas AAF/LDF" suma Kuma, Mora, Gorgon, Strider, Nyx, Hellcat, Mohawk, Gryphon, Buzzard y Zamak MRL al Oeste. Con Western Sahara, Reaction Forces o Expeditionary Forces cargados (la línea 6 los carga) suma también sus vehículos. La IA no los compra. No está en las misiones de 1985 ni de Vietnam. |
| AI: Teams | 8 Slots | Cuántas escuadras de IA tiene cada bando (antes 6). Más escuadras = más tropas y vehículos en el mapa, pero menos FPS: si el juego va lento, bájalo a 6. |
| INCOME: Delay | 1 min | Cada cuánto cobran los dos bandos (antes 2 min). Más rápido = la IA compra soldados y vehículos más seguido. |
| UPGRADE: Max Time needed for upgrades | 400 s | Tope de tiempo de cada investigación (antes 600 s): el comandante (tú o la IA) llega antes a tanques, helicópteros de ataque y aviones. |
| AI: Team Size (AI) / (Player) | 12 / 12 | Soldados por escuadra de IA y máximo de soldados en tu propia escuadra. |
| AI: Commander | Enabled | La IA dirige tu bando (compra, construye, manda escuadras) si tú no eres el comandante. |
| RESPAWN: Structure Range (FOB/Town camps) | dice 1 KM | En nuestras copias un parche lo deja **sin límite**: al morir puedes reaparecer en cualquier FOB de tu bando, aunque el lobby diga 1 KM. Para los campamentos de pueblo manda "RESPAWN: Camps". |
| RESPAWN: Camps | Classic | "Classic" = solo puedes reaparecer en los campamentos del pueblo más cercano a donde moriste. "Nearby Camps" = en el campamento de cualquier pueblo tuyo, también el más cercano al frente. Deja "RESPAWN: Enemy near" como está: en "Disabled" no ofrece ningún campamento. En Malden evita los campamentos de Cancon: uno está mal puesto en la misión original, a casi 3 km de altura. |
| RESPAWN: Mobile Range (AI/Medical vehicles) | 2000 m | Distancia a la que puedes reaparecer junto a un vehículo médico o tomar el control de un soldado de IA de tu escuadra. |
| RESPAWN: Penalty | Start with last Gear | Reapareces gratis con el mismo equipo con el que moriste, incluidas las armas recogidas del suelo (la escopeta de KJW colgada a la espalda se cae con el cuerpo). "Full Gear Price" = pagas otra vez tu última compra y, si no te alcanza, sales con el equipo básico; "Disabled" = gratis con tu última compra. |
| RESPAWN: AI Members | Enabled only near units | Cuándo reaparecen los soldados de IA de tu escuadra. |
| INCOME: Starting Funds / Supply (East / West) | iguales: 15000 / S10000 (BECTI clásica: 20000 / S25000; invasiones: Este 30000 / S25000, comandante 40000) | Los dos bandos arrancan con lo mismo, salvo en las invasiones (ahí el Este, normalmente tu bando, arranca con más). Para un enemigo más difícil, sube los del Este; si te parece muy fuerte, bájalos o sube los del Oeste. |
| PERSIST: Mode / Save periode | Enabled, 10 min | La partida se guarda sola cada 10 min (una partida guardada por misión) y al volver a entrar se carga, con las bases y los pueblos donde estaban. "Disabled" = partida suelta: no carga ni guarda y no toca tu partida guardada. "Reset (1 Save for each mission)" = empieza de cero y borra la partida guardada en el primer guardado, a los 10 min; en esa primera partida no salen los vehículos iniciales. |
| WEATHER: Inital Time / Day Duration / Night Duration | 5 AM / 12 h / 1 h | Hora de inicio y cuánto duran el día y la noche (en horas reales). |
| WEATHER: Simple presets | Sunny | Clima fijo soleado, aleatorio "normal" o totalmente aleatorio. |
| VISUAL: View Distance / Terrain Grid | 3 KM / Free | Distancia de visión máxima que permite la misión y detalle del terreno. |
| Main Camo | auto | Camuflaje del equipo: desierto en Altis, Stratis y Takistán; invierno en Chernarus invierno; selva en Tanoa; estándar en el resto. Se puede forzar. |
| ADDON: CUP Support / ADDON: RHS Support | según la misión | "set as main" = esa fuente manda en unidades y vehículos. Las misiones "con RHS" ya lo traen así. |
| US / Soviet / Ukrainian / CDF / CHDKZ Side | según la misión | Qué naciones juegan y en qué bando. Cambiarlo cambia la misión entera; mejor usar otra misión del catálogo. |

### Solo en las misiones de Tanoa (V6, 2026-10-16)

Las misiones de Tanoa (A: línea 10; B: línea 12) son la versión de prueba de la V6. Cuando estén pulidas, esto se pasará a los demás mapas.

**Valores por defecto distintos a las otras misiones:**
- AI: Teams 6, con escuadras de 10.
- TOWNS: Independent y Occupation en "Easier".
- TOWNS: Amount "Large" (44 pueblos).
- Vehicles Recycling Delay 10 min.
- RESPAWN: Camps "Nearby Camps".
- TOWNS: Purchase Units "Cars, basic infantry and support trucks".

| Parámetro (como sale en el lobby) | Por defecto | Para qué sirve y cuándo cambiarlo |
|---|---|---|
| VIOC rendimiento: Borrar vehiculos abandonados | Lejos de jugadores y fuera de bases | Borra los vehículos vacíos que nadie usa. Nunca toca el HQ, uno con un jugador a menos de 1 km, uno que tu grupo usó en los últimos 30 min ni tus camiones de apoyo. Para conservar uno, quédate cerca o marca `cursorObject setVariable ["VIOC_KEEP", true, true];` en la consola. |
| VIOC rendimiento: Tiempo de los restos de vehiculos destruidos | 3 min | Si hay un jugador a menos de 100 m, el resto se queda. |
| VIOC rendimiento: Tiempo de los cuerpos en el suelo | 5 min | Las armas tiradas duran lo mismo. |
| VIOC rendimiento: Maximo de cuerpos a la vez | 120 | Por encima del tope se retiran los cuerpos más viejos que no tengan jugadores a 300 m. |
| VIOC rendimiento: Limpiar armas tiradas en el suelo | Si | "No" = las armas no se borran nunca (original). |
| VIOC rendimiento: Aviones y helicopteros de ataque en las guarniciones | No | En el original, los pueblos grandes sacaban cazas ya en vuelo; ahora los aviones están estacionados en los aeródromos. |
| VIOC rendimiento: Un pueblo se activa con enemigos por debajo de esta altura | 20 m | Un avión que pasa no despierta pueblos. Un helicóptero que baja o la infantería los activan unos 5 s más tarde. 50 m = original. |
| VIOC rendimiento: Tope de soldados IA en el mapa | 500 | Si se pasa, las guarniciones nuevas salen más chicas (nunca menos del 40 %) y las escuadras de IA esperan para comprar. Nunca afecta a tus compras ni a tu escuadra. |
| VIOC rendimiento: Crear las guarniciones repartidas en varios frames | Si | Evita los tirones al activar un pueblo grande. |
| VIOC rendimiento: Monitor en pantalla | No | FPS, cantidad de IA, vehículos, cuerpos, armas y pueblos activos. También se enciende con `VIOC_PERF_HUD = true;` en la consola. |
| VIOC: Bases avanzadas | Si | En los pueblos tomados compras infantería y vehículos ligeros; en las bases militares, también pesados; junto a un aeródromo, también helicópteros y aviones. Lo comprado aparece allí. Abre el menú de compra a menos de 200 m del centro, de un campamento o de la plataforma del aeródromo. Con el Centro de Control, la lista muestra primero las bases avanzadas más cercanas. Nada se cobra si hay enemigos a 300 m o se pierde el sitio. |
| VIOC: Bases avanzadas: exigir esa misma fabrica viva en la base principal | Si | Para comprar blindados en una base avanzada hace falta la fábrica pesada en tu base. Lo mismo con el cuartel, la fábrica ligera y la de aviones. |
| VIOC: Bases avanzadas: recargo sobre el precio normal | 0 % | Para hacer más caro comprar en el frente (10, 25 o 50 %). |
| VIOC: Bases avanzadas: reaparecer en las mas cercanas sin enemigos | Si | El menú de reaparición suma las 6 bases avanzadas más cercanas. |
| VIOC: Aerodromos capturados | Si | Tus aviones y helicópteros, y los de la IA aliada, cargan combustible, se reparan y se rearman gratis si se paran en un aeródromo tuyo sin enemigos a 300 m. La IA vuelve sola cuando le falta combustible o munición. |
| VIOC: Aerodromos: antiaereas, antitanque y ametralladora extra | Si | Hasta 2 antiaéreos, 1 antitanque y 1 ametralladora por aeródromo, del bando dueño. |
| VIOC: Aerodromos enemigos: aviones y helicopteros estacionados | Si, y un helicóptero despega si atacas | Aviones vacíos y cerrados en los aeródromos de los bandos sin jugadores (máximo 10 en el mapa). Al capturar el aeródromo desaparecen. |
| VIOC: Pedir operaciones especiales a la IA | Si | Acción "PEDIR: Operacion especial (IA)", aunque no seas el comandante. En el mapa eliges el tipo (paracaidistas, helicóptero o, de noche, a pie), 4, 6 u 8 soldados y si se unen a tu grupo. Haces clic en el objetivo y lo pagas con tus fondos. "Si a mitad de precio" la abarata. |
| VIOC: Operaciones especiales pedidas: espera minima entre un pedido y el siguiente | 2 min | Espera entre pedidos de un mismo jugador ("Sin espera" a 30 min). |
| VIOC: Operaciones especiales simultaneas | 5 | Máximo de operaciones a la vez: por bando para la IA y por jugador para tus pedidos. Ningún pueblo recibe dos operaciones del mismo bando a la vez. Para que la IA llegue a 5, baja "una como maximo cada" a 10 min; con 20 min llega a unas 2-3. "1" = como antes. |
| VIOC: Info del arma en el menu de equipo | Si | Botón "Info del arma" en el menú de equipo. Muestra para qué sirve el arma, su munición compatible (con precio si la vende tu tienda), los accesorios por ranura, los modos de fuego y cómo se usa un lanzador. |
| VIOC: Ropa de selva en mapas tropicales | Si | En Tanoa todos los bandos y los pueblos van con camuflaje de selva o verano, y la guerrilla con ropa tropical. Además, la IA no usa armas de 2035 ni de la Segunda Guerra Mundial. |
| VIOC: Solo vehiculos contemporaneos | Si | Quita de fábricas, escuadras de IA, pueblos, defensas y partidas guardadas los vehículos de la Segunda Guerra Mundial y los futuristas de 2035. En Tanoa salen 44: Marshall, Slammer, Panther, Ghost Hawk, Blackfoot, Black Wasp, Blackfish, C-47/AC-47; Qilin, Marid, Varsuk, Kajman, Shikra, Xi'an... El T-34-85 de la guerrilla pasa a ser un T-55. Se quedan los reales de RHS y CUP (UH-60, AH-64, M1, Bradley, BMP, HMMWV...). "Estricto" también quita Hunter, Prowler, Ifrit, MH-9, Orca, Tempest y el SAM/radar de Arma. "Si, pero conservar WS/RF/EF" deja los vehículos de Western Sahara, Reaction Forces y Expeditionary Forces que pasen las reglas. |
| VIOC: Transporte de la IA | Si | Las escuadras de infantería de la IA suben a un camión o blindado cuando el objetivo está lejos. Bajan cerca del objetivo o al ser atacadas, y el vehículo se queda de apoyo. Primero usan vehículos abandonados de su bando; si no hay, compran uno (máximo 6 por bando). Los vehículos con asientos libres llevan infantería. "Si, pero sin compras" = solo sus vehículos y los abandonados. Tú no puedes subir a los transportes que maneja la IA. |
| VIOC: Transporte de la IA: subir si el objetivo esta a mas de | 900 m | Distancia al objetivo desde la que la infantería sube. |
| VIOC: Transporte de la IA: bajar a esta distancia del objetivo | 500 m | Antes, la misión bajaba a los pasajeros a 850 m. |
| VIOC: Tripulacion de los vehiculos comprados | Si: como en el editor | Antes, la misión creaba tripulantes para puestos que RHS y CUP bloquean o que no existen. En un M1A2 SEP sobraban 2 o 3 soldados que se quedaban de pie fuera, y pasaba en 57 de los 621 vehículos que se venden. Ahora cada vehículo trae su tripulación real (un M1: conductor, artillero, jefe y cargador). Si alguno no logra subir, se borra a los 3 s y se te devuelve su costo. "Turrets" ya no llena los asientos de pasajero: para eso compra infantería. |
| VIOC: Pedir dron de reconocimiento (UAV) | Si | Acción "PEDIR: Dron de reconocimiento (UAV)": marcas una zona en el mapa y llega un dron que da vueltas sobre ella (EE.UU.: MQ-9 Reaper sin armas a ~1500 m; Rusia: Pchela-1T a ~500 m). Si no tienes terminal de UAV, te dan una conectada al dron; "VER CAMARA DEL DRON" te pasa a su cámara (N = térmica). Uno por jugador y 3 por bando. Si lo derriban, no se devuelve el dinero. |
| VIOC: Dron: precio / duracion / espera entre drones | 2500 / 20 min / 5 min | Se ajustan en el lobby. La espera empieza cuando el dron anterior se retira. |
| VIOC: Dron: marcar en tu mapa los enemigos que detecta | Si | Cada 15 s, los enemigos que ve el dron (a menos de 1.5 km del centro) aparecen como marcadores solo para ti. |
| VIOC: Escuadras aereas de la IA por bando | 2 | Cuántas escuadras de IA de cada bando, aliado y enemigo, usan helicópteros y aviones. El original era el 5 % de las escuadras: 1 con 6. Siempre quedan al menos 2 escuadras de tierra. Necesitan la fábrica de aviones y sus mejoras. |
| VIOC: Saltar con los paracaidistas | Solo en mis pedidos | En el panel de PEDIR, "Saltar con ellos (yo tambien)". Viajas en el avión con un equipo como el de ellos y un paracaídas dirigible, y saltas con el equipo. Si no lo abres (ESPACIO o rueda: Abrir paracaídas), se abre solo a 160 m. Tu equipo anterior vuelve con "Recuperar mi equipo anterior" en la base, un FOB, un camión de munición o un pueblo tuyo. Con las otras opciones también puedes unirte a los saltos de la IA ("UNIRSE AL SALTO", 60 s): estando a 500 m de su base de salida, o desde cualquier parte. |
| VIOC: Pueblos en juego (lista curada) | Solo islas con puente (24) | En Tanoa quedan 24 pueblos: la capital, las ciudades grandes, los aeródromos, los puertos y los sitios militares e industriales de la isla principal y de la isla sureste (unida por un puente). "Todas las islas" deja 27. "No" usa TOWNS: Amount como antes. Cambiarla invalida la partida guardada. |
| VIOC: Capital fortificada | Si | Georgetown lleva 3 veces la guarnición normal (hasta 8 grupos) y 6 estáticas extra (2 antiaéreas, 2 antitanque y 2 ametralladoras). Ninguna base arranca a menos de 2.5 km de ella. |
| VIOC: Controles en las entradas de la capital | 4 | Controles de carretera a 280–450 m del centro: barreras, señal, bandera y ametralladora, y un antitanque en uno de cada dos. Son del dueño de la capital (la insurgencia al empezar) y cambian de dueño 3 min después de una captura. El carril queda libre para los convoyes. |
| VIOC: Victoria por la capital y los aerodromos | Si | Gana quien mantenga la capital y todos los pueblos de aeródromo en juego (en Tanoa: Aeroport de Tanoa, Lijnhaven y La Rochelle Aerodrome) durante el tiempo elegido. Vale también para el enemigo. Siguen las victorias originales. |
| VIOC: Victoria: tiempo manteniendo la capital y los aerodromos | 5 min | 2, 5 o 10 min. Se avisa a todos cada minuto. |
| VIOC: Ordenes de fuego (artillero y artilleria) | Si | Acciones "ORDEN: Atacar donde miro" y "ORDEN: Atacar punto (mapa)". El artillero de tu vehículo, o los vehículos de tu grupo, disparan sin que digas "fire". Contra un enemigo disparan directo; contra un punto o un edificio, fuego de supresión. Con el M1128 usan munición explosiva para puntos e infantería, AP para blindados y HEAT para vehículos ligeros. Con artillería (M109, HIMARS, M270, 2S1, 2S3, BM-21) eliges munición y disparos (1/3/5/10) y ves el alcance y el tiempo de llegada. No disparan con tropas propias a menos de 50 m (fuego directo) o de 150 m (artillería). "Artillero: disparar a discreción" deja a la tripulación en fuego libre. |
| VIOC: Ordenes de fuego: duracion del fuego directo / artilleria | 20 s / sin demora | El fuego directo dura de 10 a 45 s. La artillería puede ir sin demora o con la demora de "ARTILLERY: Delay". Respeta "ARTILLERY: Setup". |
| VIOC: Apoyo aereo a pedido (A-10 y Ghostrider) | Si | Acción "PEDIR: Apoyo aereo (A-10 / Ghostrider)". **A-10:** marcas el blanco y eliges cañón, cohetes, bombas guiadas o mixto. Llega, hace una pasada en picado y se va. Si juegas en el Este, es un Su-25 sin bombas guiadas. **Ghostrider:** un C-130J da vueltas a 2.5 km de altura y durante 5 min dispara 105 mm y ráfagas de 30 mm sobre los enemigos del punto. Con "GHOSTRIDER: nuevo blanco" lo mueves. El Este no tiene Ghostrider. Ninguno dispara con tropas propias a menos de 75 m (100 m las bombas). Si el ataque no sale, se devuelve el dinero; si lo derriban, no. |
| VIOC: A-10: precio / espera | 6000 / 10 min | Por bando. |
| VIOC: Ghostrider: precio / fuego / espera / espera si lo derriban | 12000 / 5 min / 15 min / 30 min | Si lo derriban, el siguiente tarda 30 min (se puede cambiar). |
| VIOC: Tacticas de la IA | Si | La IA de los dos bandos coordina varias escuadras: contraataques, pinzas y defensa en pinza (abajo). LAMBS sigue manejando las tácticas dentro de cada escuadra. |
| VIOC: Contraataques de la IA | Todos los pueblos | Si un bando pierde un pueblo, entre 2 y 5 min después lo contraataca con 2 escuadras (3 si es la capital o un aeródromo). La capital y los aeródromos siempre; los demás pueblos según su valor. "Solo pueblos importantes" deja nada más la capital y los aeródromos. |
| VIOC: Contraataques: insistencia | Cada 10 min durante 30 min | Cuántas veces reintenta un contraataque fallido. "Un solo intento" o "cada 6 min durante 45 min". |
| VIOC: Ataques en pinza | Ataques y defensa | Si varias escuadras atacan el mismo pueblo, se reúnen en los flancos (en camión si hace falta) y entran a la vez, suprimiendo. En defensa, hasta 2 patrullas de la guarnición rodean a los atacantes; la capital conserva al menos la mitad de sus grupos. |
| VIOC: Contraataques: aviso vago al bando atacado | No | "Si" avisa sin detalles que hay movimiento enemigo hacia un pueblo. |
| VIOC: Historia de la guerra | Si | Graba quién domina cada pueblo, los avisos importantes (capital, aeródromos, bases, apoyo aéreo) y dónde están las escuadras. Con la acción "Ver historia de la guerra" se ve en el mapa en cualquier momento, acelerada y con los colores de cada bando. Se guarda en tu perfil (las 3 últimas partidas de cada misión). Se puede exportar a HTML o GIF con `python3 tools/war_replay.py export --html ~/Desktop/guerra.html --gif ~/Desktop/guerra.gif`. |
| VIOC: Historia de la guerra: mostrarla sola al terminar | Si | Al acabar la partida se abre el mapa con la repetición. Se puede cerrar antes con Esc. |
| VIOC: Historia de la guerra: duración de la repetición | 60 s | 30, 60 o 120 s para toda la guerra. |

### Solo en la misión B: "CW: Colombia y EE.UU. contra la narcoinsurgencia" (Tanoa, 2026-10-17)

- Se juega con la **línea 12**. El Oeste es Colombia, con apoyo de EE.UU. desde el nivel medio. El Este es la narcoinsurgencia.
- Valores por defecto: los mismos de las misiones de Tanoa, salvo "TOWNS: Independent" en **Easy**: los pueblos libres tienen poca milicia.

| Parámetro (como sale en el lobby) | Por defecto | Para qué sirve y cuándo cambiarlo |
|---|---|---|
| VIOC: Mision B: inicio fijo | Si | El gobierno empieza con Georgetown, Georgetown Port, Regina, Nicolet y los 3 aeródromos. La insurgencia, con Tanouka y los aserraderos Norte y Sur. El resto es de la milicia local. Las bases quedan fijas: la tuya junto a la capital y la insurgente en el centro. Solo cuenta al empezar una partida nueva. |
| VIOC: Mision B: ofensiva insurgente inicial | Si | Hacia el minuto 2 la insurgencia ataca Georgetown, Aeroport de Tanoa, La Rochelle Aerodrome y Lijnhaven con sus escuadras y 5 grupos nuevos con técnicas (45 hombres como máximo). Los que sobrevivan lejos de ti se retiran a los 45 min. |
| VIOC: Mision B: reglas de victoria | Si | Ganas si dominas todos los pueblos. Pierdes si la insurgencia mantiene Georgetown y Aeroport de Tanoa a la vez durante el tiempo de "Victoria: tiempo" (5 min), en cualquier momento. Si la insurgencia se queda sin pueblos, corre la cuenta de abajo. |
| VIOC: Mision B: minutos para la insurgencia acorralada | 8 | Con 0 pueblos, la insurgencia tiene este tiempo para tomar uno. Si no lo logra, ganas. |
| VIOC: Apoyo de EE.UU. para Colombia | Si | Desde el nivel medio: vehículos, aeronaves y armas de EE.UU. en la fábrica y la tienda, 4 especialistas (Javelin, Stinger, M107, M240) y sus fuerzas especiales en las operaciones especiales. |
| VIOC: Estilo narco en mapas tropicales | Si | La insurgencia (ChDKZ) se viste y se arma como narco tropical: Hilux artilladas, blindado viejo capturado, Mi-8, UH-1H y An-2, lanchas. Sus operaciones especiales son "Sicarios" y "Selva". |

## Misiones CW (Warfare)

Se juegan con la **línea 6** (las de Tanoa, con la **10**; "CW: Selva 2026", con la **1V**), en **MULTIPLAYER → SERVER BROWSER → Host Server (LAN)**: eliges el mapa a la izquierda y la misión a la derecha. Todas empiezan por "CW:" (o "BECTI clásica") para encontrarlas juntas. Cada una guarda su partida por separado. Las marcadas "Requiere CUP y RHS" también: esas líneas ya traen RHS.

### Malden 2035

- **CW: EE.UU. vs Rusia (pueblos con guerrilla)**
  - Warfare clásico. EE.UU. contra Rusia por los pueblos de Malden, que al inicio defiende la guerrilla local. 6 escuadras IA de 12 por bando y guardado cada 10 min. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Malden V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799676)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU.Malden`
- **CW: EE.UU. vs Rusia (frente)**
  - El mapa arranca partido a la mitad: los pueblos cercanos a tu base son tuyos y el resto es ruso. Sin guerrilla; peleas contra rusos desde el primer minuto. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Malden V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799676)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_frente.Malden`
- **CW: Ucrania vs Rusia (pueblos con guerrilla)**
  - Ucrania (Oeste) contra Rusia (Este) por los pueblos de Malden, que al inicio defiende la guerrilla local. Fuerzas ucranianas de CUP con camuflaje MM-14. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Malden V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799676)
  - Carpeta: `mpmissions/VIOBECTICW_UA_RU.Malden`
- **CW: Ucrania vs Rusia (frente)**
  - Ucrania contra Rusia con el mapa partido a la mitad desde el inicio, sin guerrilla. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Malden V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799676)
  - Carpeta: `mpmissions/VIOBECTICW_UA_RU_frente.Malden`
- **CW: OTAN y Ucrania vs Rusia (frente)**
  - Escalada hipotética: EE.UU. y Ucrania en el mismo bando contra Rusia, con el mapa partido a la mitad. Las fábricas mezclan vehículos de las dos naciones. Sin probar todavía. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Malden V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799676)
  - Carpeta: `mpmissions/VIOBECTICW_OTANUA_RU_frente.Malden`
- **BECTI clásica: más enemigos (equipo 2035)**
  - VIO-BECTI original con el equipo futurista del juego (OTAN contra CSAT). Más escuadras IA y pueblos más defendidos. No necesita mods.
  - Se arma desde: [VIO-BECTI Vanilla Malden 2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2484718479)
  - Carpeta: `mpmissions/VIOBECTI_config.Malden`
- **CW: EE.UU. vs Rusia con RHS (frente)**
  - Ejércitos completos de RHS: EE.UU. (M1A2, Bradley, Stryker, Apache, Black Hawk) contra Rusia (T-72B3, T-90, BMP-3, Ka-52), con el mapa partido a la mitad. La guerrilla de los pueblos sigue siendo de CUP. Requiere CUP y RHS (USAF, AFRF y GREF).
  - Se arma desde: [VIO-BECTI-CW Malden V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799676)
  - Carpeta: `mpmissions/VIOBECTICW_RHS_US_RU_frente.Malden`

### Livonia

- **CW: Báltico 2026 (OTAN vs Rusia)**
  - Livonia, bosques y pueblos tipo Polonia o Lituania. La OTAN (representada por el Ejército de EE.UU.) contra Rusia con el frente partido, como un choque en la brecha de Suwałki. Requiere CUP y el DLC Contact.
  - Se arma desde: [VIO-BECTI-CW Livonia V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974800207)
  - Carpeta: `mpmissions/VIOBECTICW_OTAN_RU_baltico.Enoch`
- **CW: Bosques de Járkov (Ucrania vs Rusia, frente)**
  - Livonia, bosques y pueblos de Europa del Este: Ucrania contra Rusia con el frente partido a la mitad, como en los bosques de Járkov e Izium. Requiere CUP y el DLC Contact.
  - Se arma desde: [VIO-BECTI-CW Livonia V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974800207)
  - Carpeta: `mpmissions/VIOBECTICW_UA_RU_livonia.Enoch`

### Takistan

- **CW: Desierto, Siria 2018 (EE.UU. vs Rusia)**
  - Takistán con camuflaje desértico automático. EE.UU. contra fuerzas rusas con el frente partido, como el choque de Khasham en Siria (2018). Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Takistan V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=3180125933)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_desierto.Takistan`
- **CW: Desierto con RHS (EE.UU. vs Rusia, frente)**
  - Takistán con los ejércitos completos de RHS: EE.UU. (M1A2, Bradley, Stryker, Apache, Black Hawk) contra Rusia (T-72B3, T-90, BMP-3, Ka-52), frente partido y camuflaje desértico. Requiere CUP y RHS.
  - Se arma desde: [VIO-BECTI-CW Takistan V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=3180125933)
  - Carpeta: `mpmissions/VIOBECTICW_RHS_US_RU_takistan.Takistan`

### Tanoa

- **CW: Crisis en el Pacífico (EE.UU. vs Rusia)**
  - Tanoa con camuflaje de selva automático. EE.UU. contra Rusia por islas cuyos pueblos defiende al inicio la guerrilla local. Requiere CUP y el DLC Apex.
  - Se arma desde: [VIO-BECTI-CW Tanoa V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799271)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_pacifico.Tanoa`
- **CW: Pacífico con RHS (OTAN vs Rusia)**
  - Tanoa con los ejércitos completos de RHS: la OTAN (Ejército de EE.UU.) contra Rusia por islas cuyos pueblos defiende al inicio la guerrilla local. Camuflaje de selva automático. Requiere CUP, RHS y el DLC Apex.
  - Se arma desde: [VIO-BECTI-CW Tanoa V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799271)
  - Carpeta: `mpmissions/VIOBECTICW_RHS_US_RU_tanoa.Tanoa`
- **CW: Colombia y EE.UU. contra la narcoinsurgencia (Tanoa)**
  - Tanoa. El Oeste es Colombia (Ejercito Nacional, Infanteria de Marina, Fuerza Aerea y Policia) con apoyo de EE. UU. (blindados, artilleria, AH-64, A-10, drones) contra la narcoinsurgencia. Requiere CUP, RHS, el mod Colombian Armed Forces RHS y los DLC Apex y Jets.
  - Se arma desde: [VIO-BECTI-CW Tanoa V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974799271)
  - Carpeta: `mpmissions/VIOBECTICW_COL_tanoa.Tanoa`

### Altis

- **CW: Guerra en el Mediterráneo (EE.UU. vs Rusia)**
  - Altis, el mapa más grande, con camuflaje desértico automático. EE.UU. contra Rusia por los pueblos, que al inicio defiende la guerrilla local. Más pueblos significa más IA: vigila los FPS. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Altis 2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=1758094892)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_mediterraneo.Altis`
- **CW: Invasión rusa del Mediterráneo (con guerrilla local)**
  - Rusia (Este) desembarca en Altis con poca tierra y más dinero inicial. Los pueblos cercanos los defiende la guerrilla local y el resto, EE.UU. (Oeste). Puedes jugar de invasor o de defensor; las escuadras IA quedan activas en los dos bandos. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Altis 2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=1758094892)
  - Carpeta: `mpmissions/VIOBECTICW_INVASION_RU_altis.Altis`

### Stratis

- **CW: Stratis, partida rápida (EE.UU. vs Rusia, frente)**
  - Isla chica para partidas cortas e intensas: EE.UU. contra Rusia con el frente partido desde el inicio. Requiere CUP.
  - Se arma desde: [VIO-BECTI-CW Stratis V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2974798605)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_stratis.Stratis`

### Weferlingen (verano)

- **CW: Alemania 1985, Bundeswehr vs NVA (frente)**
  - Guerra Fría en Weferlingen, junto a la frontera interalemana: la Bundeswehr (Leopard 1, Marder, G3) contra el ejército de Alemania Oriental (T-55, BMP-1, AK). El mapa arranca partido a la mitad y el frente queda a 1.5-3 km de cada base. Requiere el DLC Global Mobilization (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994391699)
  - Carpeta: `mpmissions/VIOBECTICW_GM_BW_NVA_frente.gm_weferlingen_summer`
- **CW: Alemania 1985, invasión del Pacto de Varsovia (con partisanos)**
  - El ejército de Alemania Oriental cruza la frontera: empieza con los pueblos a menos de 3 km de su base y con más dinero. Los pueblos siguientes los defienden partisanos (guerrilla de CUP) y los del fondo la Bundeswehr. Elige el Oeste para defender o el Este para invadir. Requiere Global Mobilization y CUP (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994391699)
  - Carpeta: `mpmissions/VIOBECTICW_GM_INVASION_NVA.gm_weferlingen_summer`
- **CW: Alemania 2026, EE.UU. vs Rusia (pueblos con guerrilla)**
  - Warfare clásico, estilo War Welcome, en los campos y pueblos alemanes de Weferlingen: EE.UU. contra Rusia por pueblos que al inicio defiende la guerrilla local. Requiere CUP y el DLC Global Mobilization para el mapa (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994391699)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_weferlingen.gm_weferlingen_summer`
- **CW: Ucrania 2026 en campo abierto (Ucrania vs Rusia, frente)**
  - Llanuras de cultivo, bosquecillos y pueblos pequeños, como en el frente del este de Ucrania. Fuerzas ucranianas de CUP contra Rusia, con el mapa partido a la mitad y el frente a 1.5-3 km de cada base. Requiere CUP y el DLC Global Mobilization para el mapa (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994391699)
  - Carpeta: `mpmissions/VIOBECTICW_UA_RU_weferlingen.gm_weferlingen_summer`
- **CW: OTAN vs Pacto de Varsovia, 1985 y moderno mezclados (experimental)**
  - Bundeswehr y EE.UU. contra Alemania Oriental y Rusia en Weferlingen. Las dos Alemanias son de 1985 (Global Mobilization) y EE.UU. y Rusia son modernos (CUP), así que conviven épocas: Leopard 1 junto a M1A2. Es la variante que funciona de 'Bundeswehr y EE.UU. contra los soviéticos'. Requiere Global Mobilization y CUP (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994391699)
  - Carpeta: `mpmissions/VIOBECTICW_GM_OTAN_PACTO.gm_weferlingen_summer`
- **CW: Alemania con RHS (EE.UU. vs Rusia, frente)**
  - EE.UU. contra Rusia con unidades y vehículos de RHS en Weferlingen, mapa partido a la mitad y frente cerca de las bases. Requiere CUP, RHS y el DLC Global Mobilization para el mapa (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994391699)
  - Carpeta: `mpmissions/VIOBECTICW_RHS_US_RU_weferlingen.gm_weferlingen_summer`

### Weferlingen (invierno)

- **CW: Invierno de 1985, Bundeswehr vs NVA (frente)**
  - Lo mismo en Weferlingen nevado: las dos Alemanias con uniformes de invierno (parka) y vehículos blancos, que la misión elige sola en este mapa. El mapa arranca partido a la mitad. Requiere el DLC Global Mobilization (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen W V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994392454)
  - Carpeta: `mpmissions/VIOBECTICW_GM_BW_NVA_invierno.gm_weferlingen_winter`
- **CW: Invierno en campo abierto (Ucrania vs Rusia, frente)**
  - Los mismos campos de Weferlingen, nevados: Ucrania contra Rusia con ropa de invierno, mapa partido a la mitad y frente cerca de las bases. Requiere CUP y el DLC Global Mobilization para el mapa (línea 6).
  - Se arma desde: [VIO-BECTI-CW Wefferlingen W V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=2994392454)
  - Carpeta: `mpmissions/VIOBECTICW_UA_RU_wef_invierno.gm_weferlingen_winter`

### Cam Lao Nam

- **CW: Vietnam 1968, EE.UU. vs Vietnam del Norte (frente)**
  - Selva, arrozales y ríos de Cam Lao Nam: el ejército de EE.UU. (con milicias CIDG; M113, M48, Huey, Cobra, F-4) contra el ejército de Vietnam del Norte (PT-76, T-54, MiG-21). Con S.O.G. la misión siempre arranca con el mapa partido a la mitad. Se juega con la línea 8 (Vietnam), en cualquiera de los dos bandos. Requiere el DLC S.O.G. Prairie Fire.
  - Se arma desde: [VIO-BECTI-CW Cam Lao Nam V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=3180139142)
  - Carpeta: `mpmissions/VIOBECTICW_SOG_US_PAVN_frente.Cam_Lao_Nam`
- **CW: Selva 2026, EE.UU. vs Rusia (frente)**
  - Guerra moderna en la selva y los arrozales de Cam Lao Nam: EE.UU. contra Rusia (CUP) con camuflaje de selva. Con S.O.G. cargado la misión siempre arranca con el mapa partido a la mitad. Requiere CUP y el DLC S.O.G. Prairie Fire para el mapa (línea 1V).
  - Se arma desde: [VIO-BECTI-CW Cam Lao Nam V2.0.6](https://steamcommunity.com/sharedfiles/filedetails/?id=3180139142)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_selva.Cam_Lao_Nam`

### Everon (CWA)

- **CW: Everon 1985, Bundeswehr vs NVA (frente)**
  - Guerra Fría en Everon, la isla de Operation Flashpoint: la Bundeswehr (Leopard 1, Marder, G3) contra el ejército de Alemania Oriental (T-55, BMP-1, AK). El mapa arranca partido a la mitad y el frente queda a 1.5-3 km de cada base, en el centro de la isla. Misión generada por nosotros, todavía sin probar en el juego. Requiere el DLC Global Mobilization, CUP y CUP Terrains - CWA (línea 6).
  - Se arma desde: `work/vio_port/VIOBECTICW_EVERON.Eden` (`tools/vio_port.py build`)
  - Carpeta: `mpmissions/VIOBECTICW_GM_BW_NVA_everon.Eden`
- **CW: Everon 2026, EE.UU. vs Rusia (pueblos con guerrilla)**
  - Warfare clásico en Everon, la isla de Operation Flashpoint: EE.UU. contra Rusia por 23 pueblos que al inicio defiende la guerrilla local, del aeródromo del norte a Saint Pierre en el sureste. Las bases suelen arrancar en el norte y en un valle del sureste. 6 escuadras IA de 12 por bando y guardado cada 10 min. Misión generada por nosotros, todavía sin probar en el juego. Requiere CUP y CUP Terrains - CWA (línea 6).
  - Se arma desde: `work/vio_port/VIOBECTICW_EVERON.Eden` (`tools/vio_port.py build`)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_everon.Eden`
- **CW: Everon 2026, EE.UU. vs Rusia (frente)**
  - Everon partido a la mitad desde el primer minuto: los pueblos cercanos a tu base son tuyos y el resto es ruso, sin guerrilla. Las bases arrancan en el centro de la isla con el primer pueblo enemigo a 1.5-3 km. Misión generada por nosotros, todavía sin probar en el juego. Requiere CUP y CUP Terrains - CWA (línea 6).
  - Se arma desde: `work/vio_port/VIOBECTICW_EVERON.Eden` (`tools/vio_port.py build`)
  - Carpeta: `mpmissions/VIOBECTICW_US_RU_everon_frente.Eden`
- **CW: Everon 1985, invasión del Pacto de Varsovia (con partisanos)**
  - Como en la campaña de Operation Flashpoint, el Pacto de Varsovia (aquí el ejército de Alemania Oriental) desembarca en Everon: empieza con los pueblos a menos de 3 km de su base y con más dinero. Los pueblos siguientes los defienden partisanos (guerrilla de CUP) y los del fondo la Bundeswehr. Elige el Oeste para defender o el Este para invadir. Misión generada por nosotros, todavía sin probar en el juego. Requiere Global Mobilization, CUP y CUP Terrains - CWA (línea 6).
  - Se arma desde: `work/vio_port/VIOBECTICW_EVERON.Eden` (`tools/vio_port.py build`)
  - Carpeta: `mpmissions/VIOBECTICW_GM_INVASION_everon.Eden`

## Otras misiones y campañas

- **Ukraine war (29 misiones, guerra de Ucrania en el mapa Krayina)**
  - Dónde: Un jugador → Escenarios → "Ukraine war"; eliges la misión en un tablero. La 26 "Glory Ukraine" es la campaña larga que se guarda sola.
  - Línea de lanzamiento: 2 (o 2b, con drones extra)
  - Ojo: Al arrancar el juego sale el aviso "No entry ... land_guardhouse_03_gate_f.scope": viene del mapa Krayina (gc_krayina.pbo) y el autor de la misión dice que se ignore. Pulsa CLOSE y luego CONTINUE.
- **Antistasi Ultimate (tú diriges la guerrilla)**
  - Dónde: MULTIPLAYER → Host Server (LAN) → mapa → Antistasi Ultimate → puesto de comandante → New game → Parameters → Factions. Combinaciones: Chernarus (Ocupante CUP CDF, Invasor CUP AFRF, Rebeldes CUP NAPA, Rivales CUP ChDKZ); Takistán (Ocupante CUP Takistani Army, Invasor CUP US Army Arid, Rebeldes milicia takistaní, Game Mode "Reb. vs Occ. and Inv."); Livonia ("Switch enemy sides", Ocupante CUP AFRF, Invasor OTAN, Rebeldes NAPA); narcos en Tanoa o Isla Pera.
  - Línea de lanzamiento: 5
  - Ojo: Se guarda solo; igual guarda en el mapa del cuartel antes de salir. No uses la línea 6 (trae PiR y RHS).
