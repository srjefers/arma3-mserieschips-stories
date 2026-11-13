# Ideas de misiones: UMB Colombia y Lingor

Banco de ideas de operaciones realistas e inmersivas, jugadas solo contra la IA en Arma 3 (puerto Mac 2.22, eON).

## Alcance y límites de este documento

- Solo se leyeron `README.md` y `CLAUDE.md`, más el contexto que dio el dueño (mods, DLC, mapas). **No** se leyeron
  `docs/ESCENARIOS.md` ni `tools/vio_doc_params.md`, así que los nombres internos de los sistemas `VIOC_*` no se citan:
  hay que mirarlos en `tools/vio_patches/` antes de reutilizar código.
- **No se incluyen nombres de clases** (unidades, vehículos, armas). Todo lo que dependa de una clase concreta de CUP,
  RHS, Colombian Armed Forces RHS o Toyota's Of War queda como **a verificar** con el Config Viewer del Editor.
- Los datos históricos están de memoria, sin consulta en línea. Lo marcado "a verificar" conviene contrastarlo antes de
  usarlo en un briefing o en documentación pública.
- Presupuesto de IA: 150-250 activas como máximo (`-maxMem=16383`). Cada idea indica cuánto usa.

---

## 1. Top 5 (orden recomendado)

| # | Misión | Mapa | Bando del jugador | Esfuerzo | Por qué primero |
|---|---|---|---|---|---|
| 1 | **Cóndor caído** (D3, CSAR) | UMB Colombia | EE.UU. vs Rusia y mercenarios | **Bajo** | Misión corta, un solo objetivo móvil, reutiliza apoyo aéreo y voces. Sirve de banco de pruebas del formato "escenario de un jugador". |
| 2 | **Nido de Cóndor** (A1, redada a laboratorio y pista) | UMB Colombia | EE.UU. vs narcos y mercenarios | **Medio** | Base de un generador de objetivos aleatorios que luego alimenta a A2 (Cacería del Patrón) y C2. Usa mercenarios ION y operaciones especiales ya hechas. |
| 3 | **Firebase Khasham** (D1, base asediada) | Lingor | EE.UU. vs Rusia y mercenarios | **Medio** | Aprovecha al máximo A-10, AC-130 "Ghostrider" y MQ-9, que ya existen. Poca lógica nueva: oleadas y fuego de apoyo. |
| 4 | **Plaza sitiada** (C1, defender al jefe de zona) | Lingor | Mercenarios vs Colombia | **Medio** | Único rol mercenario sencillo; invierte los sistemas ION y de asalto aéreo de la IA. |
| 5 | **Operación Jaque** (B1, engaño y rescate) | Lingor | Colombia vs narcos | **Alto** | La más distintiva y la más cercana a una operación real. Requiere mecánica de engaño (`setCaptive`, reglas de enfrentamiento) y guion de fases. |

### Cómo reutilizar lo que ya existe

- **Mercenarios ION:** como guardia del jefe (A1, A2), como enemigo "tipo Wagner" mezclando equipo (D1) o como el jugador (C1, C2, C3).
- **Operaciones especiales (EE.UU. y Colombia):** extraer su lógica de aparición y órdenes del parche de Tanoa para usarla
  como "apoyo que puedes pedir" o como escuadras aliadas de la IA (D3, A1, B1).
- **Apoyo aéreo (A-10, AC-130, MQ-9):** como menú de fuego de apoyo (D1, B2, D3), con retraso y munición limitados por misión.
- **Asalto aéreo de la IA:** como fuerza de reacción rápida enemiga (C1, C2, C3) o como transporte aliado (A1, B2).
- **Voces de radio en español:** para el menú de mando y las llamadas de apoyo; coste de desarrollo casi nulo.
- **FPV (ArmaFPV + Drongo + CL AI Drone Warfare):** operadores enemigos en defensas (D1, C1) y amenaza para convoyes (C3).
  Coste de rendimiento alto: probar con pocos operadores primero.
- **Historia animada de la guerra:** repetir la idea como "resumen de operación" al final (línea de tiempo de la misión).
- **Estrategia de código:** no hacer parches de BECTI. Estas misiones son independientes, así que hay que extraer las
  piezas reutilizables de los `VIOC_*` a una pequeña biblioteca común (`OPS_*` o similar, nombre a decidir) con las
  reglas de `CLAUDE.md`: ASCII, prefijo propio, compatible con servidor dedicado.

---

## 2. Detalle de todas las ideas

Leyenda de duración: tiempo de juego real aproximado.

### A. EE.UU. contra narcos y mercenarios

#### A1. Nido de Cóndor — UMB Colombia
- **Bandos:** EE.UU. (aliado: Colombia, solo transporte y cobertura) vs narcos y mercenarios ION contratados como seguridad.
- **Rol:** jefe de un equipo de operaciones especiales de EE.UU. (6-8 hombres) con asesor de la DEA. Unidad exacta a verificar según lo que ofrezca CUP/RHS USAF.
- **Objetivo:** destruir un laboratorio de cocaína en la selva, capturar o neutralizar al químico/responsable y llevarse los documentos y discos de inteligencia.
- **Fases:**
  1. *Infiltración:* helicóptero a un claro lejos del objetivo, o lancha por río/costa. Sin carreteras: caminata de 1-3 km.
  2. *Acción:* reconocimiento del campamento (dron pequeño o binoculares), eliminar guardias, asaltar el laboratorio, asegurar documentos.
  3. *Extracción:* helicóptero a un segundo punto de recogida; la guardia ION pide refuerzos por radio si se les da tiempo.
- **Ganar/perder:** ganas con documentos y al menos el responsable capturado, y con el equipo en la zona de extracción. Pierdes si muere el jefe, si se destruye más de la mitad del equipo o si se agota el tiempo antes de extraer.
- **Duración:** 45-75 min.
- **Realismo:**
  - Operación Blast Furnace (Bolivia, 1986): helicópteros del Ejército de EE.UU. con agentes de la DEA contra laboratorios.
  - Operación Snowcap (DEA, Andes, 1987-1994).
  - Equipos FAST de la DEA (Afganistán, y Honduras desde 2012; detalle a verificar).
  - Realismo táctico: el laboratorio se defiende con trampas y una guardia pequeña, no con 50 hombres.
- **Rejugable:**
  - Posición del laboratorio entre 4-6 sitios candidatos (claros de selva en UMB).
  - Tamaño de la guardia y presencia de ION (sí/no).
  - Hora del día y niebla.
  - Dos vías de infiltración (aire/agua) según el sitio.
  - Un "invitado inesperado": un convoy de relevo que llega a mitad de misión.
- **IA estimada:** 40-70.
- **Recursos:** mercenarios ION (CUP), ropa y armas RHS USAF, helicópteros de Helicopters DLC y de la facción colombiana (a verificar), LAMBS para la reacción de la IA, voces de radio en español para la comunicación con la base colombiana.

#### A2. Cacería del Patrón — Lingor
- **Bandos:** EE.UU. con Colombia vs un capo, su red de lugartenientes y ION.
- **Rol:** oficial paramilitar de la CIA o jefe de equipo de una unidad de élite de EE.UU. con un analista en el centro de mando.
- **Objetivo:** localizar y capturar o eliminar a un objetivo de alto valor (HVT) cuya posición cambia. Se descubre con inteligencia, no con el mapa.
- **Fases:**
  1. *Búsqueda:* seguir pistas (interceptaciones, un informante, un vehículo vigilado) hasta fijar su ubicación aproximada.
  2. *Fijar:* cerco discreto con drones y observadores.
  3. *Acción y extracción:* asalto nocturno y salida antes de que lleguen refuerzos desde Maruko.
- **Ganar/perder:** ganas capturando o eliminando al HVT; pierdes si pasan N horas simuladas sin fijarlo o si huye del mapa (cruza un río/frontera).
- **Duración:** 90-150 min (buena candidata a *mini campaña* de 3-4 misiones).
- **Realismo:** la caza de Pablo Escobar (el Bloque de Búsqueda colombiano, apoyado por inteligencia de señales de EE.UU.; el papel exacto de EE.UU. a verificar) y el ciclo "encontrar, fijar, acabar".
- **Rejugable:** el HVT empieza en una de 5-6 casas de seguridad; sus rutas y escoltas se sortean; las pistas son aleatorias.
- **IA estimada:** 80-120 en total, repartida por zonas.
- **Recursos:** facciones narco de Colombian Armed Forces RHS, ION, Toyota's Of War como vehículos de escolta, el dron MQ-9 y el menú de apoyo existente.

#### A3. Interdicción en la costa — UMB Colombia
- **Bandos:** EE.UU. (Guardia Costera / marina) vs traficantes marítimos y mercenarios.
- **Rol:** jefe de un equipo de abordaje (LEDET) en una lancha de interceptación con helicóptero de apoyo.
- **Objetivo:** detener una lancha rápida o un semisumergible ("narcosubmarino") y capturar la carga y a la tripulación.
- **Fases:**
  1. *Detección:* un dron o patrullera señala un contacto en la costa.
  2. *Persecución y abordaje:* velocidad, fuego de advertencia, abordaje.
  3. *Seguridad:* asegurar la carga y entregarla a la marina colombiana.
- **Ganar/perder:** ganas incautando la carga; pierdes si la carga se hunde (tripulación la abandona) o si el contacto llega a aguas fuera de zona.
- **Duración:** 20-40 min.
- **Realismo:** Operación Martillo (esfuerzo multinacional contra el tráfico por el Pacífico y el Caribe, desde 2012) y las incautaciones de semisumergibles. Detalles de ROE a verificar.
- **Rejugable:** tipo de embarcación, rumbo, resistencia (huir, tirar la carga, disparar).
- **IA estimada:** < 30.
- **Recursos:** lanchas y submarinos de DLC (Jets/Laws of War/Contact; clases a verificar), mapa UMB Colombia (costa grande). Cuidado: las lanchas con IA son frágiles, probar el comportamiento.

### B. Colombia contra narcos y mercenarios

#### B1. Operación Jaque — Lingor (o UMB Colombia)
- **Bandos:** Ejército de Colombia (inteligencia militar) vs grupo guerrillero/narco que mantiene rehenes.
- **Rol:** jefe de un equipo de inteligencia militar y fuerzas especiales camuflado, en un helicóptero con livery civil.
- **Objetivo:** rescatar a los rehenes (3-4 civiles/militares) sin combate, haciendo que los carceleros los entreguen.
- **Fases:**
  1. *Preparación:* interceptar las comunicaciones y elegir la cobertura (organización humanitaria ficticia).
  2. *Engaño:* aterrizar en el campamento, convencer al jefe de transferir a los rehenes. Los guardias están en alerta y el jugador conserva las armas ocultas.
  3. *Extracción:* subir a los rehenes y despegar sin disparar; si estalla un tiroteo, plan B con apoyo aéreo.
- **Ganar/perder:** ganas con todos los rehenes a bordo; pierdes si matan a más de uno o al jefe de misión. Disparar primero reduce la puntuación (final "limpio" vs "ruidoso").
- **Duración:** 30-50 min.
- **Realismo:** Operación Jaque, 2 de julio de 2008: 15 rehenes, incluida Ingrid Betancourt y tres contratistas estadounidenses, rescatados sin disparos. Los agentes se hicieron pasar por una misión humanitaria y el helicóptero llevaba livery civil. **Nota de diseño:** el uso del emblema de la Cruz Roja fue polémico, por lo que conviene un livery genérico en el juego.
- **Rejugable:** guardias con distinto grado de desconfianza; variantes de los códigos que hay que decir; un traidor que advierte al campamento en algunas partidas.
- **Mecánica clave:** `setCaptive` y control de lo que la IA considera hostil; un diálogo simple por menú contextual. Probar cómo reaccionan las IA de LAMBS a un helicóptero que aterriza.
- **IA estimada:** 25-40.
- **Recursos:** guerrilla de Colombian Armed Forces RHS, helicópteros colombianos (a verificar), civiles para los rehenes (clase a verificar).

#### B2. Fénix: golpe desde el aire — UMB Colombia
- **Bandos:** Colombia vs un campamento guerrillero/narco al otro lado de una "frontera" ficticia (zona fuera del mapa o isla).
- **Rol:** controlador aéreo de la Fuerza Aérea o jefe de un equipo de fuerzas especiales que marca el objetivo.
- **Objetivo:** confirmar el blanco, designar el bombardeo y asegurar el campamento después con un asalto aéreo.
- **Fases:**
  1. *Infiltración:* helicóptero a una colina de observación.
  2. *Marcar y bombardear:* designar con láser o radio; ataque aéreo (A-10 o aviones colombianos, a verificar).
  3. *Asalto:* helicópteros dejan una fuerza de reacción; se confirma la baja del objetivo y se extrae.
- **Ganar/perder:** ganas confirmando la baja del jefe; pierdes si el ataque cae sobre civiles o si el equipo se descubre antes.
- **Duración:** 35-60 min.
- **Realismo:** Operación Fénix, 1 de marzo de 2008, bombardeo del campamento de Raúl Reyes en Angostura (Ecuador), seguido de asalto aéreo; hubo crisis diplomática. La ayuda de inteligencia de EE.UU. se ha reportado (detalle a verificar).
- **Rejugable:** posición del campamento, hora, presencia de civiles (riesgo moral), tiempo para designar.
- **IA estimada:** 40-60.
- **Recursos:** menú de A-10/AC-130 ya hecho, Ghostrider, voces en español, la Fuerza Aérea del mod colombiano (clases a verificar).

#### B3. Orión: cerco y registro en Maruko — Lingor
- **Bandos:** Ejército y Policía de Colombia vs milicias urbanas y francotiradores.
- **Rol:** comandante de una compañía mixta Ejército-Policía.
- **Objetivo:** asegurar barrios de Maruko, desarmar milicias y proteger a los civiles.
- **Fases:** cerco de la zona; entrada por sectores con registro de casas; defensa ante contraataques y francotiradores; entrega a la policía.
- **Ganar/perder:** ganas asegurando X barrios con pocas bajas civiles; pierdes si los civiles muertos superan un umbral (reutiliza la penalización de Tanoa) o si cae un sector.
- **Duración:** 60-90 min.
- **Realismo:** Operación Orión (Medellín, octubre de 2002): intervención militar en la Comuna 13; controvertida y con daño a civiles. Es el modelo de *contrainsurgencia urbana* con sus dilemas; conviene tratarla con ese matiz.
- **Rejugable:** milicianos disfrazados de civiles, ubicación de explosivos y francotiradores, barrios aleatorios.
- **IA estimada:** 80-120 (presupuesto límite; usar `enableDynamicSimulation` y reaparición por barrio).
- **Recursos:** insurgentes encubiertos, IED y coche bomba de los parches existentes; policía colombiana del mod.

### C. Mercenarios contra Colombia (juegas como mercenario)

#### C1. Plaza sitiada — Lingor
- **Bandos:** mercenarios (ION) contratados por un jefe de zona vs Ejército y Policía de Colombia.
- **Rol:** jefe del equipo de seguridad (10-12 contratistas) del complejo del jefe.
- **Objetivo:** mantener el complejo hasta que llegue la extracción del jefe (helicóptero o lancha) y evacuarlo vivo.
- **Fases:** preparación (colocar defensas y minas, elegir posiciones); oleadas del ejército con asalto aéreo y FPV; extracción del jefe con ventana de tiempo.
- **Ganar/perder:** ganas con el jefe vivo en el medio de extracción; pierdes si muere, si cae el complejo o si la extracción es destruida.
- **Duración:** 45-75 min.
- **Realismo:** guardia privada de un capo (modelo de seguridad de organizaciones narco) y la lógica de contrato de las PMC. Referencias de contrato: Executive Outcomes en Sierra Leona (1995) y Wagner en África (detalles a verificar).
- **Rejugable:** la dirección del ataque, el tamaño de las oleadas, la hora y el estado del clima se sortean; el jugador elige su equipo antes de empezar (presupuesto).
- **IA estimada:** 80-140.
- **Recursos:** ION PMC (CUP), Toyota's Of War, LAMBS para que el ejército use el terreno, FPV enemigo (limitar a pocos), asalto aéreo de la IA.

#### C2. Pista clandestina — UMB Colombia
- **Bandos:** mercenarios vs Colombia (Ejército, Fuerza Aérea).
- **Rol:** jefe de un equipo de 8 contratistas, con un piloto contratado.
- **Objetivo:** tomar una pista remota, cargar un avión y salir antes de que llegue la reacción.
- **Fases:** infiltración en lancha por la costa; toma silenciosa de la pista (controles, vigilantes); espera del avión y carga con un reloj; huida del área.
- **Ganar/perder:** ganas con la carga en el aire; pierdes si el ejército cierra la pista o derriba el avión.
- **Duración:** 40-60 min.
- **Realismo:** logística aérea clandestina en la región; en la vida real el control del espacio aéreo y el radar son lo que decide, así que el reloj se acelera con el ruido (combate no silenciado).
- **Rejugable:** pista (3-4 candidatas), carga (droga, armas, dinero), presencia de radar, fuerza de reacción (helicópteros o patrulleras).
- **IA estimada:** 50-90.
- **Recursos:** lanchas de DLC, ION, helicópteros de reacción del Ejército y el asalto aéreo de la IA.

#### C3. Rescate en tránsito — Lingor
- **Bandos:** mercenarios (por encargo) vs Ejército y Policía.
- **Rol:** líder de un equipo de ataque de un convoy.
- **Objetivo:** liberar a un capo detenido durante su traslado por la selva y sacarlo del mapa.
- **Fases:** vigilar el convoy (ruta variable); emboscada en un puente o vado; extracción antes de la reacción.
- **Ganar/perder:** ganas con el prisionero libre en la zona de extracción; pierdes si muere o si el convoy llega a su destino.
- **Duración:** 30-50 min.
- **Realismo:** las emboscadas a traslados de presos y los rescates por comando; analogía con operaciones fallidas de contratistas (p. ej. la incursión de Silvercorp contra Venezuela en 2020, que fracasó; detalles a verificar). El fracaso de ese tipo de operaciones aporta tensión: poca información y mal equipo.
- **Rejugable:** ruta y composición del convoy, escoltas, puntos de emboscada (puentes y vados de Lingor).
- **IA estimada:** 40-70.
- **Recursos:** vehículos artillados de Toyota's Of War, convoyes y puentes del mapa.

### D. EE.UU. contra Rusia y mercenarios

#### D1. Firebase Khasham — Lingor
- **Bandos:** EE.UU. con fuerza aliada (colombiana o local) vs mercenarios rusos (estilo Wagner) y apoyo ruso.
- **Rol:** sargento de un equipo de operaciones especiales (ODA) que dirige el fuego de apoyo.
- **Objetivo:** defender una base avanzada en un puente/vado durante una noche hasta la llegada del relevo.
- **Fases:**
  1. *Preparación:* repartir al socio local, minas y ametralladoras.
  2. *Defensa:* oleadas de vehículos y tropa; se piden A-10, AC-130 y MQ-9.
  3. *Contraataque o extracción:* al amanecer, limpieza y relevo.
- **Ganar/perder:** ganas manteniendo la base hasta el relevo; pierdes si el puente cae o si las bajas del equipo superan un umbral.
- **Duración:** 50-80 min.
- **Realismo:** batalla de Khasham, 7-8 de febrero de 2018 (Siria): una columna con mercenarios del grupo Wagner y fuerzas aliadas del gobierno sirio atacó una posición de fuerzas de EE.UU. y de socios locales; EE.UU. respondió con aviones, helicópteros y artillería. Las cifras de bajas rusas siguen **discutidas** (a verificar).
- **Rejugable:** orden y tipo de oleadas, dirección de la columna, FPV enemigo, clima, fallos de comunicación.
- **IA estimada:** 100-160.
- **Recursos:** apoyo aéreo ya hecho, RHS AFRF (rusos), mezcla con CUP para el aspecto "mercenario" (a verificar), voces en español para el aliado.

#### D2. Corredor del Caribe — UMB Colombia
- **Bandos:** EE.UU. (marines y operaciones especiales) vs fuerzas rusas y mercenarios que operan un puesto de escucha en una isla.
- **Rol:** jefe de una unidad de reconocimiento de la infantería de marina.
- **Objetivo:** neutralizar una estación de señales/radar y recuperar datos sin provocar un incidente internacional.
- **Fases:** desembarco nocturno; ataque al puesto; extracción antes de que llegue una fuerza naval rusa.
- **Ganar/perder:** ganas con los datos y sin bajas civiles ni de la tripulación; pierdes si se hunde la lancha de extracción o si se pierde el sigilo ante el barco ruso.
- **Duración:** 40-60 min.
- **Realismo:** **ficción plausible**, no operación real. Hay informes de presencia rusa y de contratistas privados en Venezuela alrededor de 2019 (a verificar).
- **Rejugable:** isla, guarnición, presencia del barco, hora.
- **IA estimada:** 50-80.
- **Recursos:** RHS AFRF, USAF/USMC de RHS y CUP, lanchas y helicópteros de los DLC (clases a verificar).

#### D3. Cóndor caído (CSAR) — UMB Colombia
- **Bandos:** EE.UU. vs fuerzas rusas y mercenarios que buscan al piloto.
- **Rol:** jefe de un equipo de rescate (PJ o infantería) en un helicóptero con escolta.
- **Objetivo:** recuperar a un piloto derribado en zona hostil.
- **Fases:**
  1. *Localización:* baliza de emergencia, el piloto se esconde y se mueve.
  2. *Aproximación y recogida:* helicóptero a un punto seguro; contacto con el piloto.
  3. *Extracción:* salir antes de que el enemigo cierre el cerco.
- **Ganar/perder:** ganas con el piloto vivo a bordo; pierdes si lo capturan o si se agota el combustible/tiempo.
- **Duración:** 20-35 min.
- **Realismo:** el rescate del capitán Scott O'Grady (Bosnia, 1995, sacado por marines tras seis días) y la lógica de los rescates de pilotos con apoyo aéreo cercano. Detalles de procedimientos a verificar.
- **Rejugable:** punto de derribo, estado del piloto (herido o no), cerco enemigo, hora, clima.
- **IA estimada:** 30-60.
- **Recursos:** Jets DLC para el piloto, Ghostrider/MQ-9 para vigilar, voces de radio, LAMBS para la búsqueda.

---

## 3. Análisis técnico: ¿LAN o escenario de un jugador?

### Datos de partida (comprobados en `README.md` y `CLAUDE.md`)
- BECTI/VIO-CW **exige** "Multiplayer LAN" y en un jugador ignora los parámetros del lobby.
- Objetivo del código actual: servidor alojado (`isServer && hasInterface` verdaderos), compatible con servidor dedicado.

Estas misiones **no** son Warfare, así que no heredan esa restricción: la decisión es de diseño, no obligada.

### Comparación

| Aspecto | Multiplayer LAN (host) | Escenario de un jugador (menú Escenarios) | Mini campaña (addon de campaña) |
|---|---|---|---|
| **Facilidad para jugar** | Pasos extra: Multijugador → Host LAN → mapa → misión → lobby. | Mejor: se elige en Escenarios y se juega. Dónde aparecen las misiones guardadas desde el Editor en el menú: **a verificar** en 2.22 Mac. | Mejor aún para historias seguidas; pero se carga como mod. |
| **Guardado y carga** | No hay guardado de partida en multijugador. Una partida perdida se pierde. | **Sí:** guardado manual y puntos de control. Cuidado con guardados grandes y con scripts largos (ver abajo). | Sí, igual que escenario, más el progreso entre misiones. |
| **Reaparición / reinicio** | Plantillas de reaparición del motor disponibles. | La muerte lleva a "Reiniciar / Cargar", sin reaparición. Para misiones cortas es lo realista. Para otras: final propio con `endMission`. | Igual; el estado pasa entre misiones con variables en el perfil (a verificar) o con la API de campaña. |
| **Parámetros** | Lobby (`description.ext` → `Params`). | **No hay lobby** (a verificar en 2.22 Mac si muestra los parámetros). Alternativas: ver más abajo. | Igual que escenario, con valores heredados de la misión anterior. |
| **Scripts de servidor** | Funcionan tal cual. | Casi todos funcionan: en un jugador `isServer` es verdadero y `hasInterface` también; `publicVariable` y `remoteExec` se ejecutan en local. Ver riesgos abajo. | Igual. |
| **Rendimiento Mac** | Algo más pesado (simulación de red del anfitrión). | Algo más ligero; cuidado con los guardados con muchas IA. | Igual que escenario. |
| **Workshop** | Se puede publicar; el jugador necesita los mods como requisitos. | Igual. | Se publica como mod/addon; necesita empaquetado (PBO) y firmas opcionales. |

### Parámetros sin lobby (por orden de recomendación)
1. **Menú dentro de la misión:** una "mesa de planificación" (objeto con `addAction`) que abre un diálogo propio
   (definido en `description.ext`) o una cadena de menús, con la dificultad, el tamaño de la guardia, la hora, etc.
   Funciona igual en un jugador y en multijugador, no necesita mods y se puede guardar con la partida.
2. **Ajustes de CBA** (`CBA_fnc_addSetting` y `cba_settings.sqf` de la misión): están en el menú de opciones de CBA, son globales a todas
   las misiones salvo que la misión los fije. Buenos para parámetros avanzados (límite de IA, desactivar FPV).
3. **Perfil** (`profileNamespace`): para recordar la última elección entre sesiones; opcional, con `try/catch` y
   sin depender de ello. Alerta: la regla de `CLAUDE.md` pide copia de seguridad y permiso antes de tocar el perfil de Arma.
4. **Presets fijos** (fácil / normal / difícil) elegidos al principio: el camino más barato para un primer prototipo.

### Riesgos de los scripts de servidor en un jugador
- `isServer` es verdadero y `isMultiplayer` falso. Envolver las rutas que dependan de `remoteExecutedOwner` en una
  comprobación de `isMultiplayer`; su valor en un jugador está **a verificar**.
- `initServer.sqf` debería ejecutarse en un jugador, pero **verificarlo** con un `diag_log` antes de apoyarse en él.
- Al cargar un guardado **no se vuelven a ejecutar** los `init`: hay que usar el evento `Loaded` de misión para restaurar
  controladores, interfaz y funciones por fotogramas. Guardar el estado en variables, no en scripts largos con `sleep`.
- Los bucles `spawn` con `sleep` se conservan, pero los controladores de CBA y los de mods pueden perderse tras cargar: probar el ciclo guardar-cargar en cada fase.
- Mantener la **compatibilidad con servidor dedicado** (regla del proyecto): no usar `player` en lógica de servidor ni asumir un único jugador en las partes comunes.
- `callExtension` y DLL: no se usan (no funcionan en el puerto).

### Rendimiento en Mac
- Presupuesto de 150-250 IA activas. Para misiones tipo Khasham o Plaza (100-160 IA), usar simulación dinámica y reaparición por oleadas, no todo de golpe.
- Un guardado con muchas IA y vehículos tarda más y pesa más: ofrecer guardados solo en límites de fase.
- FPV con IA (ArmaFPV + CL AI Drone Warfare) es la parte más cara; limitar el número de operadores y medir con `tools/arma_memlog.sh`.
- Diagnóstico en Mac: no hay `.rpt`; leer `eon.txt` (ver `CLAUDE.md`).

### Compartir en el Workshop
- Un escenario o una campaña sin parches de BECTI se puede compartir, con CBA/CUP/RHS/etc. como elementos requeridos. **No** se puede incluir contenido de VIO-BECTI (ver `NOTICE.md`), y las misiones Warfare siguen siendo parches, no ficheros publicables.
- Publicar desde el Editor en el puerto Mac: **a verificar**. Si no funciona, las alternativas son compartir el código fuente en el repo público (con la limpieza de privacidad de `CLAUDE.md`).
- Una campaña requiere empaquetar un addon: `tools/pbo_tool.py` ya existe, pero si sabe **escribir** PBO es algo a comprobar. Cualquier addon local que se instale fuera del repo debe pasar por `tools/track.sh`.

### Recomendación por tipo de misión

| Tipo | Formato recomendado | Por qué |
|---|---|---|
| Cortas, un objetivo (D3 Cóndor caído, A3 Interdicción, B1 Jaque, C3 Rescate en tránsito) | **Escenario de un jugador** | Guardado entre fases, sin reaparición (realista), arranque rápido. Parámetros con un menú o presets. |
| Medias con oleadas (A1, B2, C1, C2, D1, D2) | **Escenario de un jugador**; **Multiplayer LAN** solo si necesitas el lobby | Guardados en límites de fase; en LAN no puedes guardar. Menú de planificación para parámetros. |
| Con historia y memoria entre partes (A2 Cacería del Patrón) | **Mini campaña** de 3-4 misiones | Estado compartido entre misiones; cuesta más empaquetarla. Empezar como escenario y migrar. |
| Urbanas y largas (B3 Orión) | **Escenario**, con guardados por barrio | Mucha IA; guardar a menudo y usar la simulación dinámica. |
| Guerra continua tipo Warfare | **Multiplayer LAN** (como hoy) | Depende del lobby y de BECTI; no cambia. |

### Siguiente paso sugerido
Construir **Cóndor caído (D3)** como escenario de un jugador. Con ella se comprueba, con poco riesgo: aparición en el menú,
guardar/cargar con las IA vivas, el menú de planificación para parámetros y el comportamiento de `remoteExec`/`isServer` en un jugador.
Lo que salga bien se extrae a la biblioteca común para las demás ideas.
