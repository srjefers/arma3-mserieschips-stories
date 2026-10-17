# VIO-BECTI Vanilla Malden 2.0.6: guía de la Fase 2 (sin mods)

**Versión:** el Workshop 2484718479 tiene el código 2.0.6 (GitHub dukee02/Arma3_CTI, commit 35bdad2). Los arreglos "2.0.7" que hay en GitHub (abril de 2026) **no** están en el Workshop, así que esta guía describe la 2.0.6.

**Estado:** verificada contra el código el 2026-10-12. Falta probarla en el juego (sección h).

**Convenciones:** lo que va en `código` es el texto exacto del juego (en inglés). "(a comprobar en el juego)" marca lo que no se pudo confirmar sin jugar.

**Resumen:**
1. Suscríbete a la misión.
2. `MULTIPLAYER` > `SERVER BROWSER` > Host Server (LAN) > Malden > `VIO-BECTI V2.0.6`.
3. Toma el slot `Alpha, Team Leader` y cambia 8 parámetros (el clave: `AI: Teams…` = `4 Slots`).
4. Vota por ti y despliega el HQ.
5. Construye `Barracks` y `Control Center`, investiga y toma pueblos.
6. Mide FPS dentro de la misión para ajustar la cantidad de IA (punto h.9) y prueba el guardado. La medición fija de la Fase 1 (YAAB y Kavala) sigue pendiente para antes de la Fase 5.

## a) Suscripción y dónde aparece la misión

1. Suscríbete a **VIO-BECTI Vanilla Malden 2.0.6**: https://steamcommunity.com/sharedfiles/filedetails/?id=2484718479
   - Pesa 3.5 MB y no tiene "Required items" ni DLC requerido.
   - Es una **misión**, no un mod: no va en ninguna lista de mods.
2. Avísame cuando Steam la haya descargado. Reviso la carpeta (regla de DLLs) y lo anoto en el log.
3. Abre **Play Arma 3**, la misma build con la que probaste Warlords.
4. Ve a `MULTIPLAYER` > `SERVER BROWSER` > pestaña **Host Server**, elige **LAN** y pulsa `HOST SERVER`.
5. En la pantalla de crear partida:
   - Elige **primero el terreno Malden**. La lista de misiones solo muestra las del terreno elegido.
   - Luego elige **`VIO-BECTI V2.0.6`**. Es su `briefingName`; que aparezca con ese nombre está (a comprobar en el juego).
   - Dificultad: la misma que en Warlords. Pulsa `Play`.
6. **No** la inicies desde `SINGLEPLAYER` > `SCENARIOS`, aunque aparezca ahí. Fuera de multijugador ignora los parámetros y usa valores de respaldo distintos (entre ellos la nación LDF, que está rota). Otros quedan sin definir, y eso da errores.

## b) Lobby

**Slot:** toma el BLUFOR **`Alpha, Team Leader`**.
- Hay 35 slots:
  - 16 BLUFOR y 16 OPFOR, todos iguales (`<indicativo>, Team Leader`, de Alpha a Papa).
  - `HC_1`–`HC_3`, que son headless client: ignóralos.
- No hay slot de comandante: el comandante se vota dentro del juego.
- Deja todo lo demás **vacío** y el juego lo llena con IA:
  - Los primeros N slots de cada bando se vuelven equipos IA (N = `AI: Teams…`).
  - El resto se queda quieto en una zona de espera. Es normal.
- Si no logras aparecer (error de grupo nulo, issue #22), entra por otro slot BLUFOR.
- Revisa los parámetros cada vez que crees la partida. Si el juego los recuerda entre sesiones está (a comprobar en el juego).

**Parámetros a cambiar** (con el botón de parámetros del lobby, como en Warlords):

| Título exacto | Elige | Por defecto | Por qué |
|---|---|---|---|
| `AI: Teams (Coop disables AI on player side)` | `4 Slots` | `Disabled` | **Obligatorio.** Con `Disabled` ningún bando tiene escuadras IA y el enemigo nunca toma pueblos. El valor es por bando (4 tuyos + 4 enemigos). Está al final de la lista, bajo el separador DEBUG. Solo se lee al iniciar la misión. |
| `AI: Team Size (AI)` | `8` | `10` | Rendimiento en el Mac: los equipos IA se mantienen llenos (ver d) y los vehículos suman tripulación. También es el tope cuando compras para un equipo `[AI]`. |
| `AI: Team Size (Player)` | `12` | `20` | Tamaño máximo de tu escuadra. Rendimiento. |
| `TOWNS: Occupation` | `Easier` | `Normal` | Menos defensores cuando atacan un pueblo con dueño, sea tuyo o enemigo: en un pueblo grande, 2 grupos en vez de 4; en uno chico, 1 en vez de 2. |
| `VISUAL: View Distance` | `3 KM` | `4 KM` | Es el tope de la distancia de visión de la misión, que ya arranca en 3000 m. |
| `VISUAL: Terrain Grid` | `Free` | `Medium` | Te deja bajar el detalle del terreno (25 o 50) en `MENU: Options` > `Video Settings` para ganar FPS. |
| `PERSIST: Mode` | `Enabled (1 Save for each mission)` | `Disabled` | Activa el guardado automático (ver f). |
| `PERSIST: Save periode in seconds` | `5min` | `15 min` | Para probar el guardado pronto. Después puedes volver a `15 min`. |

**No toques:**
- `TOWNS: Starting Mode` = `Resistance`. Nunca elijas `Coop at East side…` ni `Coop at West side…`: apagan los equipos IA de un bando.
- `AI: Commander` = `Enabled`. Es lo que le da comandante al enemigo.
- Revive: es la primera fila después de `============ Respawn ============`. Déjala en su primera opción (desactivado). El texto es de Bohemia y su nombre exacto en inglés está (a comprobar en el juego).
- `INDEPENDENT Town Nation` = `AAF`. `LDF` está roto en la 2.0.6.
- `AI: Skill (all AI units)` = `30% Novice`. Mira el descuento del 1 % en la sección d.
- `INCOME: Starting Funds (East Commander)` y `(West Commander)` = `$50000`. Nunca pongas más de `$500000` (bug).
- `PERFORMANCE: On active Persistence, log unit infos to .rpt and maybe disband stuck AI teams`: nunca `Enabled AI disbanding`.

**Opcionales para más adelante:**
- `UPGRADE: Pre researched Factory level (Barracks,Wheeled,Tracked,Air,Naval,Gear)`: úsalo si el arranque se siente lento. Aplica a ambos bandos.
- `TOWNS: Amount` = `Large` (18 pueblos) o `Medium` (13) para campañas más cortas. Para ganar hay que tener todos los pueblos en juego.
- `WEATHER: Inital Time`: las etiquetas no corresponden a la hora real.
  - `5 AM` (el valor por defecto) empieza hacia las 12:26.
  - `12 AM` empieza hacia las 07:26.
  - La noche pasa 10 veces más rápido.
- `AI Vehicles locked?` = `Disabled - needed if you want to transport AI Teams`, si quieres subirte a los vehículos de los equipos IA.

## c) Primeros pasos como comandante

**1. Vota por ti (primer minuto).**
- Se abre `Commander Vote :` con `Time :` (60 s). La primera fila es `AI Commander`: **haz clic en tu nombre**.
- Solo votan los equipos con jugador humano, así que tu voto gana y aparece `You are the new Commander! Good luck!`.
- Si no votas (o cargas tarde), sale `AI Commander Selected!` y la IA manda tu bando: gasta tu dinero y tu supply y empieza tu base.
- Para arreglarlo, usa la acción `MENU: Commanding` > `Voting`. Empieza una votación nueva de 60 s: haz clic en tu nombre otra vez. Al ganar, el comandante IA desaparece en unos 5 s; sus edificios se quedan.

**2. HQ.**
- Apareces a 8–30 m de tu HQ móvil, un AMV-7 Marshall. Está cerrado: usa la acción `Unlock`.
- A 45–60 m tienes un Prowler y un Hunter gratis, sin cerrar.
- Lleva el HQ a un sitio plano a **más de 550 m de cualquier pueblo**. Más cerca despiertas la guarnición del pueblo.
- Abre `MENU: Construction (HQ)`. Aparece a ≤50 m del HQ móvil y a ≤150 m del desplegado.
- En `Building Construction` pulsa `Deploy HQ (S1000)` y colócalo.
- El despliegue cuesta **S1000 de supply**, aunque el lobby diga "$1000".
- `Mobilize HQ` es gratis, pero cada nuevo despliegue vuelve a costar S1000.
- Mientras el HQ está móvil, los demás botones salen en gris.

**3. Construye** (`MENU: Construction (HQ)` > `Build Structure`).
- Controles:
  - Clic izquierdo coloca y clic derecho cancela.
  - `Left Ctrl` y `Left Alt` rotan; `Left Shift` rota más rápido. Qué teclas del Mac equivalen está (a comprobar en el juego).
  - Las teclas de altura de las defensas no hacen nada en la 2.0.6.
- Dónde se puede construir:
  - A ≤150 m del HQ, con un máximo de 4 áreas de base.
  - Sin edificios a menos de 15 m ni personas o vehículos a menos de 10 m. Si no, sale `Building colliding: Yes` y el clic no hace nada (aparta el Prowler y el Hunter).
- Todo se construye por tiempo y puedes tener varias obras a la vez.
- `Add Worker ($100)` **no** acelera las obras en la 2.0.6: los trabajadores solo reparan. La `Online Help` está desactualizada en esto.
- No uses `Undo Structure`: no devuelve el supply y el edificio aparece igual.
- Orden sugerido: `Barracks` → `Control Center` → `Wheeled Vehicle Factory` → `Tracked Vehicle Factory` (S16,000 en total).
- **Barracks primero**: si destruyen tu HQ y no tienes ninguna fábrica, pierdes la partida.

| Estructura | Costo | Tiempo | Para qué |
|---|---|---|---|
| `Barracks` | S2000 | 60 s | Infantería; `MENU: Equipment` a ≤150 m |
| `Control Center` | S4000 | 90 s | `Teams`, `Map Commanding`, `Upgrades`, `Artillery`; comprar a ≤12.5 km |
| `Wheeled Vehicle Factory` | S4000 | 80 s | Vehículos de ruedas |
| `Tracked Vehicle Factory` | S6000 | 120 s | Vehículos de orugas (el primero es el Panther) |
| `Aircraft Factory` | S8000 | 140 s | Aeronaves |
| `Ammo Depot` | S2000 | 90 s | Rearme y camiones de munición |
| `Repair Depot` | S4000 | 90 s | Reparación, camiones de reparación y recuperadores |
| `Naval Yard` | S3000 | 80 s | Botes |

**Defensas** (`Build Defense`, se pagan en $):
- Mk30 HMG $375, Mk32 GMG $600, mortero $1500.
- Con `Defenses Auto-Manning: On` (por defecto), tus `Barracks` tripulan las estáticas a ≤500 m, hasta 30 IA.

**4. Equípate.**
- El kit inicial no trae mira, GPS ni visión nocturna, a propósito. Sí trae mapa, brújula, radio y prismáticos.
- Abre `MENU: Equipment`. Aparece a ≤150 m de unas `Barracks`, a ≤12 m del depósito de un pueblo tuyo y a ≤4 m de un FOB.
- En `Gear Purchase Menu :` elige `Target :` y pulsa `Buy`. Puedes guardar loadouts con `Create Template`.
- Desde el inicio: NLAW por $300 más $150 por misil.
- Con `Gear` 1: GPS $150, visión nocturna $150, mira 1× $100.

**5. Compra tropas.**
- Abre `MENU: Factory` a pie:
  - A ≤150 m de una fábrica.
  - A ≤50 m del depósito de un pueblo tuyo.
  - Con `Control Center`, desde cualquier punto a ≤12.5 km.
- También sirve la acción `Use Barracks` del edificio.
- En `Factory Menu`:
  1. En `Team :` elige tu grupo o un equipo `[AI] …`.
  2. En `Factory :` elige la fábrica.
  3. Ajusta los íconos de tripulación y el candado. Los vehículos salen **cerrados** por defecto.
  4. Pulsa `Purchase`.
- La unidad sale en la fábrica y se une al grupo elegido.
- Se paga al entregarse, de los fondos del comandante ($50,000 al inicio). Cada tripulante suma $150.
- Cola máxima: 20 en `Barracks`, 6 en las demás. La infantería básica cuesta $150.

**6. Investiga.**
- Ve a `MENU: Commanding` > `Upgrades` (requiere `Control Center`). En `Upgrade Menu` elige la línea y pulsa `Upgrade`.
- Solo puedes investigar una cosa a la vez (verás `Running: …`).
- Orden sugerido:
  1. `Gear` 1
  2. `Barracks` 1
  3. `Defenses` 1 (habilita el FOB)
  4. `Supply` 1
  5. `Heavy Factory` 1
  6. `Heavy Factory` 2 (Slammer)
- Total: unos S3,563 + $1,719 y unos 10.5 min.

**7. Toma pueblos.** Empieza por los chicos.
- Primero los campamentos (las banderas): tu infantería tiene que estar a ≤10 m, y tú a ≤5 m. Cada campamento paga $250 y acelera mucho la captura del pueblo.
- Luego supera en número a todos los demás en 50 m alrededor del centro del pueblo (el depósito). Verás ` <pueblo> SV:x/y` y una barra de captura.
- Si tú o alguien de tu grupo está a ≤250 m cuando el pueblo cae, cobras **$6,000** (pueblo chico) o **$12,000** (grande).
- En el depósito de un pueblo capturado puedes comprar Quadbike, Prowler y **Hunter** sin investigar nada.

**8. Si mueres.**
- Esperas 20 s y en `Respawn Menu` eliges dónde reaparecer:
  - El HQ móvil o tus estructuras.
  - Un FOB a ≤1 km de donde moriste.
  - Un vehículo médico o una IA de tu grupo a ≤600 m.
  - Los campamentos del pueblo más cercano, si moriste a ≤600 m de él.
- Reapareces con tu último equipo comprado y se cobra completo, del dinero del comandante.
- El revive está desactivado.

## d) IA: equipos aliados y enemigos

**Equipos IA (ambos bandos)**
- Con `4 Slots` hay 4 equipos tuyos y 4 enemigos. Se fijan al iniciar: cambiar el número exige reiniciar la misión.
- Cada equipo empieza así:
  - Un líder solo.
  - Orden `Take Towns`.
  - `Independent` en On (compra solo).
  - $20,000.
  - Rol `Infantry (Auto)`.
- Solo compran (3–5 unidades, como mucho cada 240 s) en dos casos:
  - El líder está a ≤150 m de una fábrica de su rol.
  - Su bando tiene un `Control Center`, lo que permite comprar a distancia (≤12.5 km).
- **Descuento oculto:** con `AI: Skill` en 10–30 % (30 % por defecto), todo lo que se entrega a un equipo IA cuesta **1/100**, en ambos bandos. Por eso los equipos viven llenos.
  - Incluye tus compras para equipos `[AI]`. Es una trampa enorme: evítala si quieres un juego justo.
  - Con `40% Rookie` o más, el descuento desaparece para todos. Los ejércitos IA serán mucho más chicos, pero apuntan mejor.
- En tu bando **nadie asigna roles**:
  - Todos tus equipos quedan como `Infantry (Auto)` y solo compran en `Barracks`.
  - No reciben compras de un comandante IA. Viven de su dinero, de su parte de los ingresos y de tus transferencias.
- No tomes el control de un grupo IA (control remoto o Zeus). Según el autor, sus líderes pueden quedar trabados hasta reiniciar.

**Menú `Teams`** (`MENU: Commanding` > `Teams`). Solo lo usa el comandante, con un `Control Center` a ≤12.5 km.
- **Rol:** en `Role:` elige `Infantry (Auto)`, `Motorized (Auto)`, `Tanks (Auto)`, `AntiAir` o `Air (Auto)`, y pulsa `Set` o `Set to All`.
  - Los roles "(Auto)" mejoran con tu investigación.
  - Cada rol necesita su fábrica.
- **Orden:** en `Order:` elige una y pulsa `Order` o `Order to All`.
  - `Take Towns`: cualquier pueblo; cambia al más cercano.
  - `Take Hold Towns`: tomar y mantener.
  - `Hold Towns/Base`: defender.
  - `Get In`, `Get Out`, `Get In (Cargo)`, `Get Out (Cargo)`.
- **Dinero:** en `Transfer:` elige de $50 a $5000 y pulsa `Transfer` o `Transfer to All`.
- **Otros:** `Independent:` On/Off con `Set`, `All AI Independent`, `No AI Independent` y `Disband Team`.

**`Map Commanding`** (mismos requisitos):
- Pasos: `Teams :` (All o un equipo) → `Orders :` → `Order Parameters :` (elige pueblo) → `Set Order` o `Set Order (Map Click)`.
- `Move` se da con un clic en el mapa.
- Con `Take Towns` + `Set Order (Map Click)` a menos de 500 m de un pueblo enemigo, el equipo va a **ese** pueblo y no cambia de objetivo.

**Nunca uses `Search and Destroy`.** Aparece en `Teams`, en `Map Commanding` y en `AI Management`, pero no está implementado en la 2.0.6: el equipo se queda sin tarea.

**Tu escuadra:** usa los comandos normales de Arma, o `MENU: Options` > `AI Management` (ventana `AI Micromanagement`) para dar órdenes soldado por soldado.

**El enemigo (comandante IA de OPFOR)**
- **Base:**
  - Construye en un orden fijo alrededor de su HQ: Control Center, Barracks, Wheeled, Repair, Ammo, Tracked y Aircraft.
  - Pone estáticas junto a sus edificios.
  - Tiene que caminar hasta ≤35 m de cada obra, así que matarlo retrasa su base.
  - Contrata hasta 4 trabajadores y 2 recuperadores.
  - Repara su HQ si tiene Repair Depot, e investiga solo si tiene su Control Center.
- **Equipos:** con 4 equipos suele tener 1 aéreo, 1 pesado y 2 de infantería. Cerca de la mitad recibe `Take Hold Towns`.
- **Ritmo:**
  - Al principio solo tiene infantería y vehículos de ruedas. Su Tracked Factory llega después de unas 15 investigaciones (51 min o más).
  - Su tanque principal llega después de 112 min de investigación o más.
  - Saca Slammers antes que él.
- **Para ganarle:**
  - Destruye su Control Center (frena su investigación) y su Repair Depot (ya no repara su HQ).
  - Los edificios de base reciben solo 1/5 del daño: usa artillería (M4 Scorcher desde `Artillery`), tanques o explosivos.
- **Bugs de la 2.0.6:**
  - Su equipo aéreo deambula sin tomar pueblos. Está arreglado solo en GitHub.
  - Podría poner estáticas Titan antes de investigarlas. Es posible, pero no se ha visto.

**Cuántas IA esperar:**
- 8 equipos de unas 8–10 unidades cada uno.
- Tu escuadra (hasta 12).
- Guarniciones de 6–12 por cada pueblo en combate.
- Estáticas tripuladas.
- Hasta 4 trabajadores enemigos.
- Unas 23 IA quietas en las zonas de espera.

## e) Economía y desbloqueos

**Dos monedas:**
- **$**: fondos del comandante ($50,000 al inicio). Con ellos pagas unidades, equipo, defensas, el FOB y la parte en $ de la investigación. Tu dinero personal ($20,000) te vuelve si pierdes el mando.
- **S**: supply del bando (S25,000 al inicio). Paga el HQ, las estructuras, la parte en S de la investigación y la reparación del HQ.
- Tu dinero, tu supply y tus pueblos se ven en `MENU: Options` (`Options & Info`: `Resources: $X / SY`, `Towns Held: n/20`).

**Ingresos:**
- Cada 90 s, cada pueblo da `$ = valor × SV/SVmáx` y `S = SV`.
- Alrededor del 37 % de ese $ va a tus equipos IA; tú recibes alrededor del 63 %.
- El SV de un pueblo solo crece si no hay enemigos a menos de 50 m: +1 cada 80 s, o de +2 a +5 con `Supply` 1–4.
- Al capturar un pueblo, su SV vuelve a 30:
  - Un pueblo recién tomado da $300 + S30 por ciclo.
  - Uno lleno da $600 + S60 (chico) o $1200 + S120 (grande).
- Cada baja enemiga paga el 40 % de su precio.
- Los recuperadores (`Buy Independent Salvager (n/2) $1500`, en la fábrica del `Repair Depot`) pagan el 30 % del precio de cada vehículo destruido que recogen.

**Los 20 pueblos de Malden:**
- **Grandes** ($1200, SV máximo 120): Moray, Le Port Harbor, Military Base, Houdan, La Trinite, Airport.
- **Chicos** ($600, SV máximo 60): La Riviere, Cancon, Chapoi, Le Port Power Plant, La Pessagne, Arudy, Dourdan, Goisse, Larche, Saint Louis, Radio Station, Small Military Base, Ruined Base, Lolisse.
- **Guarniciones:** un pueblo chico tiene 1 grupo de 6, sin tanques ni aviones. Uno grande tiene 2 grupos de 6 y puede tener blindados y aviones.

**Niveles clave** (BLUFOR). Cada nivel exige el anterior y cada tripulante suma $150.

| Línea | Nv | Costo | Tiempo | Desbloquea |
|---|---|---|---|---|
| `Gear` | 1 | S250 + $125 | 30 s | GPS, visión nocturna, telémetro, miras 1× |
| `Barracks` | 1 | S250 + $125 | 30 s | Grenadier, Autorifleman, Rifleman AT ($300) |
| `Defenses` | 1 | S188 + $94 | 60 s | FOB ($7,500 en esta versión clásica; en las misiones CW cuesta $50,000; máx. 6), Titan AT estático ($1,800) |
| `Supply` | 1 | S625 + $250 | 60 s | SV +2 cada 80 s |
| (construir `Tracked Vehicle Factory`) | 0 | — | — | IFV-6c Panther y CRV-6e Bobcat ($3,500) |
| `Heavy Factory` | 1 | S750 + $375 | 90 s | Cheetah (antiaéreo) y M4 Scorcher (artillería) ($7,000) |
| `Heavy Factory` | 2 | S1500 + $750 | 360 s | M2A1 Slammer ($10,500) |
| `Light Factory` | 1 | S250 + $125 | 60 s | Hunter ($2,000) y camiones HEMTT |
| `Light Factory` | 3 | S750 + $375 | 540 s | AMV-7 Marshall ($6,000) |
| `Gear` | 3 | S750 + $375 | 270 s | Lanzador Titan ($1,200) |
| (construir `Aircraft Factory`) | 0 | — | — | MH-9 Hummingbird ($3,000) |
| `Aircraft Factory` | 1–3 | S3750 + $1875 en total | 1050 s en total | AH-99 Blackfoot ($36,000) |

**Cómo se gana:**
- Tienes los 20 pueblos, o el enemigo se queda sin HQ vivo **y** sin ninguna `Barracks`, Wheeled, Tracked ni Aircraft. El juego lo revisa cada 15 s.
- Si destruyen tu HQ, se repara con un camión de reparación: súbete como conductor, acércate a ≤35 m y usa `Repair HQ`. Cuesta S1000 × pueblos tuyos × número de reparación.

## f) Guardar la partida

- No hay guardado manual: la misión usa su propio sistema (`PERSIST: Mode`).
- Con los valores de la tabla guarda sola cada 5 min, **sin aviso en pantalla**.
- El primer guardado llega a los 5 min más o menos, así que juega **al menos 10 min** antes de salir.

**Qué se guarda:**
- Dueños de los pueblos (el SV vuelve a 30).
- El HQ y la investigación terminada.
- Áreas de base, estructuras (también las que están en obra), FOB y defensas.
- Supply, fondos del comandante y de los equipos.
- Vehículos vacíos.

**Qué no se guarda:**
- Unidades, escuadras IA y vehículos con tripulación.
- La hora y el clima.
- La investigación en curso: su costo se pierde, así que no salgas mientras investigas.

**Cómo usarlo:**
- **Para seguir:** vuelve a crear la partida (Malden > `VIO-BECTI V2.0.6`) con el mismo `PERSIST: Mode` y cargará sola. Entra siempre desde Host Server: el autor avisa que cargar con un botón "Continue" duplica las unidades.
- **Para empezar de cero:** juega una sesión con `Reset (1 Save for each mission)`, que no carga y sobrescribe la ranura. Después vuelve a `Enabled (1 Save for each mission)`.
- **Ganar o perder** borra el guardado.
- **Evita `Enabled (1 Save for all VIO-BECTIs)`**: es una sola ranura para todas las VIO-BECTI. Si existe, una partida con `Disabled` empieza sin el Prowler y el Hunter gratis.
- **Dónde vive:** en el archivo `.vars` de tu perfil de Arma. Que el puerto Mac lo escriba y lo recargue es justo lo que vamos a probar.
- **Para cambiar `AI: Teams…` o los tamaños:** sal después de un guardado, cambia el parámetro y vuelve a crear la partida. Conservas el progreso, pero no las tropas.

## g) Problemas conocidos y soluciones

| Problema | Solución |
|---|---|
| No hay escuadras IA o el enemigo no toma pueblos | `AI: Teams…` en `1 Slot` o más (usa `4 Slots`) y `TOWNS: Starting Mode` = `Resistance` |
| La IA manda tu bando | Vota por ti; si se te pasó, `MENU: Commanding` > `Voting` |
| `Teams`, `Map Commanding`, `Upgrades` y `Artillery` salen en gris | Tienes que ser comandante y tener un `Control Center` a ≤12.5 km |
| Los equipos IA son de un solo hombre | Necesitan una fábrica de su rol a ≤150 m o un `Control Center` |
| Un equipo se queda quieto tras una orden | Le diste `Search and Destroy`, que no está implementado: dale otra orden |
| No aparece el FOB | Investiga `Defenses` 1 |
| `Building colliding: Yes` | Deja 15 m libres de edificios y 10 m libres de personas y vehículos |
| El equipo aéreo IA va y vuelve sin tomar pueblos | Bug de la 2.0.6. En tu bando usa otro rol o `Set Order (Map Click)` sobre un pueblo |
| El comandante IA con más de $500,000 deja de pasar dinero a sus equipos (error) | No subas sus fondos iniciales por encima de `$500000` |
| Ves vehículos o armas de DLC que no tienes | No podrás manejarlos, artillarlos ni comandarlos; como pasajero sí. Cómpralos con tripulación IA o evítalos. Si no tienes Karts ni Helicopters, los autos y aeronaves DLC muestran `Get in … (DLC Bypass)`, con publicidad (a comprobar en el juego). El equipo DLC que compres también muestra publicidad |
| La artillería del motor no responde | Es normal. Usa `MENU: Commanding` > `Artillery` con la pieza en **tu** grupo (180 s entre misiones). Si el marcador o el botón dejan de funcionar (issue #33, sin arreglo), avísame |
| No apareces al iniciar (grupo nulo, issue #22) | Entra por otro slot |
| Unidades o vehículos desaparecen antes de tiempo (issue #29) | No tiene arreglo; avísame |
| Líderes IA trabados en la zona de espera | Pasa si tomas el control de un grupo IA. Solo se arregla reiniciando |
| Etiquetas del lobby engañosas | `5 AM` empieza hacia las 12:26. En artillería, `120` son en realidad 180 s. `Enabled all infantry` no se puede elegir. `BASE: HQ Deploy Cost` cobra supply, no $ |
| El Mac no escribe .rpt | Dime el texto que sale en pantalla y qué estabas haciendo; mide con la consola de depuración |

## h) Qué probar y qué reportarme

1. ¿Aparece en Host Server > Malden? Dime el nombre exacto.
2. ¿Pudiste poner los 8 parámetros? Copia el texto de la fila de revive y su opción.
3. ¿Salió `Commander Vote :` y luego `You are the new Commander! Good luck!`? ¿Tuviste que usar `Voting`?
4. Prueba `Unlock` y `Deploy HQ (S1000)`, y construye `Barracks`, `Control Center` y una fábrica. ¿Qué teclas del Mac rotan los edificios?
5. En `Teams`, ¿ves 4 equipos tuyos? ¿Crecen? Cambia uno a `Motorized (Auto)` o `Tanks (Auto)`.
6. ¿En qué minuto toma OPFOR su primer pueblo? Míralo por el color de los pueblos en el mapa.
7. Termina `Gear` 1 y `Defenses` 1: ¿aparece el FOB? Compra algo para un equipo `[AI]`: ¿cuánto te cobró?
8. Toma un pueblo chico con tu grupo cerca: ¿salió `$6000 awarded for the capture of …`?
9. FPS:
   - Apaga V-Sync.
   - Pulsa `Esc` y abre la consola de depuración; como host deberías verla (a comprobar en el juego).
   - En los campos de vigilancia pon `diag_fps` y `count allUnits`.
   - Anota los valores a los 2, 30 y 60 min y durante un combate en un pueblo.
   - ¿Hay tirones cada 5 min (guardado)?
10. Guardado: juega al menos 10 min, sal y vuelve a crear la partida con los mismos parámetros. ¿Volvieron los pueblos, el HQ, los edificios, la investigación y el dinero?
11. DLC: ¿ves vehículos que no tienes (por ejemplo Rhino MGS o Huron)? ¿Puedes manejarlos? ¿Aparece `Get in … (DLC Bypass)`?
12. Opcional, solo para mirar: ¿se abre Zeus con tu tecla de Zeus? Es trampa; solo sirve para diagnosticar (a comprobar en el juego).
13. Cualquier error en pantalla, cuelgue o IA trabada: dime qué hacías y en qué minuto.

Con eso decido si subimos la IA (`6 Slots` o tamaño `10`) o la bajamos (`3 Slots`).

## Fuentes

El código 2.0.6 es github.com/dukee02/Arma3_CTI en el commit 35bdad2, carpeta `VIO-BECTI.Map_name`. Las copias del Workshop están en `research/evidencia/`.

- **Parámetros:** `vio_ws_params.hpp` líneas 8–24, 44–48, 170–187, 571–575, 595–599 y 637–671.
- **Equipos IA, compras y descuento:**
  - `vio_ws_init_server.sqf` 233–292 (equipos IA y modos Coop).
  - `update_ai.fsm` 253–289 y 342 (compras IA).
  - `Server_HandleAIPurchase.sqf` 90–93 y 118–122 (descuento).
- **Votación:** `Server_VoteForCommander.sqf` 50–92; `Events_UI_VoteMenu.sqf` 19–36; `Client_Commander_VoteEnd.sqf` 28–33; `Server_RequestCommanderVote.sqf` 39–53.
- **Menús y órdenes:**
  - `Client_AddMissionActions.sqf` 24–33.
  - `Events_UI_CommandMenu.sqf` 8–14.
  - `Events_UI_TeamsMenu.sqf` 22–37.
  - `Events_UI_MapCommandMenu.sqf` 36 y 136–175.
  - `Functions_FSM_UpdateAI.sqf` 549–551.
  - `squad_west.sqf` 253, 439, 590, 627 y 816.
  - `Rsc/Dialogs.hpp` 2842–3040, 3226–3298 y 4885–4932.
- **Base:** `Base.sqf` 80–188; `Events_UI_BuildMenu.sqf` 17–49 y 186–189; `Client_PlacingBuilding.sqf` 75.
- **Investigación:** `Upgrades.sqf` 57–142, 185–217, 225–311 y 392–405.
- **Guardado:** `vio_ws_init_server.sqf` 180–185, 211–229 y 361–475; `Server_SaveToProfile.sqf` 41–52 y 241; `Server_LoadFromProfile.sqf` 44–66.
- **Pueblos y slots:** `vio_becti_malden_2484718479_mission.sqm` líneas 89, 187–4074 y 1419–3062.
- **DLC:** `Common_HasDLC.sqf` 61; `Common_InitializeNetVehicle.sqf` 77–84.
- **Problemas abiertos:** github.com/dukee02/Arma3_CTI/issues/22, 29 y 33, y las respuestas del autor en el Workshop de la versión Altis (2484715680).