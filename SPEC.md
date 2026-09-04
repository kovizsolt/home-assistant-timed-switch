# Állapotgép specifikáció — Home Assistant / Python

> Ez a dokumentum két részből áll: **A rész** — a munkamódszer (ezt ne töröld, ez a projekt "alkotmánya"). **B rész** — a kitöltendő specifikációs sablon. A cél: olyan specifikáció, amiben nincs értelmezési rés, ezért a kód nem *értelmezése*, hanem *átirata* a specifikációnak. **Nyelvi megjegyzés:** a próza–szótár nyelvi megosztás szabálya kanonikusan a `CLAUDE.md` 0. pontjában van rögzítve. Az alábbi B2 szótár emiatt szándékosan tér el az A2/2 pont illusztrációjától, ami egy általános, projekt-független példát mutat be.

---

# A RÉSZ — MUNKAMÓDSZER

## A1. Alapelv

A prózai leírásban mindig maradnak hézagok, amiket az AI csendben kitölt saját feltételezésekkel — és nem szól, hogy feltételezett. A hibák 99%-a innen ered, nem a kódolásból.

Ezért a specifikáció **nem próza, hanem táblázat**, és minden cella ki van töltve.

## A2. A hat lépés

### 1. Táblázat, nem próza

Minden (állapot × esemény) cella kitöltve — beleértve azokat is, ahol a válasz "figyelmen kívül hagyjuk". **Üres cella = garantált hiba.**

Egy 5 állapot × 6 esemény gép = 30 cella. Mindegyikhez tartozik: célállapot, feltétel (guard), akció.

### 2. Rögzített szótár

Az állapotok, események és entity_id-k nevét **egyszer** definiáljuk, és utána szó szerint azokat használjuk, szinonimák nélkül.

Ha a specifikációban hol `elesitve`, hol `armed` szerepel, abból két állapot lesz, vagy összemosódik kettő.

Konvenció: állapotok `NAGYBETŰS_SNAKE`, események `kisbetus_snake`, entity_id-k teljes alakban (`binary_sensor.bejarati_ajto`). Ebben a projektben a szótár nyelve angol (lásd fenti nyelvi megjegyzés) — a konvenció (nagybetűs/kisbetűs snake_case) ettől függetlenül érvényes.

### 3. Peremfeltételek kimondva

Ez az, ami prózából mindig kimarad, és amitől a program a valóságban elromlik. Kötelezően megválaszolandó — lásd a B4. kérdőívet:

- Kezdőállapot HA-újraindítás után?
- Mi történik, ha egy szenzor `unknown` / `unavailable`?
- Az időzítők túlélik-e az újraindítást?
- Mi van, ha egy timer lejár, miközben más állapotban vagyunk?
- Ha két esemény szinte egyszerre érkezik, melyik nyer?
- Idempotencia: ugyanaz az esemény kétszer → az akció kétszer fut?

### 4. Előbb tesztek, csak utána kód

**Ez a legfontosabb lépés.**

A táblából először **elfogadási tesztek** készülnek: eseménysorozat → várt végállapot → várt akciók.

Példa:
```
[OTTHON] --tavozas_gomb--> [ELESITES_ALATT]
         --(60 s timer)--> [ELESITVE]
         --mozgas-------->  [RIASZT] + akció: sziréna BE
```

Ezt a fejlesztő (ember) átolvassa, **mielőtt egy sor kód is születne.** Ha egy teszt ránézésre rossz, akkor **a specifikáció volt kétértelmű**, nem a kód hibás — és ezt itt fillérekért javítjuk, nem hibakeresés közben.

### 5. Táblavezérelt implementáció

A kódban az átmeneti tábla **egy az egyben megjelenik adatszerkezetként** (dict vagy lista), a motor pedig generikus.

Tilos: szétszórt `if/elif` láncok, állapotlogika több fájlban. Előny: a tábla és a specifikáció egymás mellé tehető, az eltérés szemmel látható.

### 6. Hibajelentés eseménysorként

Nem próza ("nem jó a riasztó"), hanem konkrét eseménysor: melyik állapotban voltunk, milyen esemény jött, mi történt ténylegesen, mit vártunk helyette. Ebből azonnal látszik, melyik táblacella hibás.

A pontos sablon és az AI válaszprotokollja kanonikusan a `CLAUDE.md` 7. pontjában van rögzítve.

## A3. Két állandó utasítás az AI-nak

Ez a két utasítás olyan fontos, hogy kanonikusan, operatív formában a `CLAUDE.md`-ben van rögzítve (amit minden munkamenet elején kötelező elolvasni) — itt csak a rájuk mutató hivatkozás:

1. Kódírás előtti feltételezés-/hiányosság-lista — lásd `CLAUDE.md` 1. pont ("Kódírás előtt — KÖTELEZŐ").
2. Aktuális dokumentáció ellenőrzése emlékezet helyett — lásd `CLAUDE.md` 5. pont ("Dokumentáció, nem emlékezet").

## A4. Architekturális döntések (Home Assistant)

**Hol lakik az állapot?** Bevált minta: `input_select` helper tárolja (pl. `input_select.riaszto_allapot`). Előny: látszik a UI-on, túléli az újraindítást, bármely automatizálás olvashatja. A Python kód csak az átmeneti logikát adja hozzá.

**Futtatókörnyezet:**

| Opció | Mikor | Jellemző |
|---|---|---|
| **Pyscript** (HACS) | kis–közepes gép | tiszta Python fájlok HA-n belül, `@state_trigger` dekorátorok, legkényelmesebb |
| **AppDaemon** | összetett / hierarchikus | külön addon vagy konténer, osztályok, jól tesztelhető |
| **Custom integration** | újrafelhasználható komponens | legnagyobb befektetés, csak ha publikálni akarod |

**Komplexitás eldöntése:**

- 6–8 állapot alatt, ha minden állapot ugyanazokra az eseményekre reagál másképp → **lapos állapotgép + tábla elég.**
- **Hierarchikus** akkor kell, ha több állapotban ugyanazt a kilépési feltételt ismételgeted (pl. "bármely aktív módból → HIBA").
- Ha egymástól független dolgok futnak párhuzamosan (fűtés-mód ÉS jelenlét-mód) → **két külön állapotgép**, nem párhuzamos régiók.

---

# B RÉSZ — KITÖLTENDŐ SPECIFIKÁCIÓ

> Töltsd ki mind a hat szakaszt. Ahol nem tudsz válaszolni, írd oda: `?? — eldöntendő`. Az AI ezeket fogja először megkérdezni.

## B1. Cél és hatókör

**Mit vezérel az állapotgép (1–3 mondat):**

```
Egy általános, újrafelhasználható Home Assistant custom integráció, amely — egy komponens-példány (config entry) mindig pontosan egy vezérelt entitáshoz kötve, 1:1 — egy vezérelt entitást irányít egy cron-szerű ütemterv és a manuális vezérlés (HA-UI vagy fizikai kapcsoló — a kettő egyenértékű bemenet) kombinációjával. A vezérelt entitás domainje a felhasználó választása szerint `switch`, `input_boolean`, `light`, `script` vagy `button`; a domain-specifikus service-hívási logika: `turn_on`/`turn_off` a switch/input_boolean/light/script domainnél, `press` a button domainnél.

Az ütemterv-kiértékelés folyamatosan, a manuális felülbírálástól függetlenül fut, és mindig frissíti a belső "timed_state" (BE/KI) tulajdonságot. Alapesetben ez a cron nyers, aktuális kimenete; a `switch.<name>_timed_state` külső automatizmusból vagy UI-ból érkező állítása azonban időbélyegzett külső ütemezési parancs, amely a következő tényleges cron-találatig elsőbbséget élvez. A `timed_state` AUTO és MANUAL alatt egyaránt frissül. A belső "expected_state" ebből származik: **AUTO** módban élőben követi a "timed_state"-et; **MANUAL** módban a kézi beavatkozás értékén fagyva marad, a "timed_state" háttérbeli változásaira nem reagál azonnal — csak a MANUAL-ból való visszatéréskor veszi át a pillanatnyi "timed_state" értéket. Azt szabályozzuk, hogy az "expected_state" ténylegesen eljusson-e a fizikai kapcsolóhoz.

Egy külön, periodikus állapot-ellenőrzés (poller, `state_sync` esemény) szinkronban tartja a virtuális célt és a fizikai kapcsoló állapotát, amikor nincs aktív felülbírálás — ez a failsafe mechanizmus elveszett service call, HA- vagy hálózati kiesés esetére.

Manuális beavatkozás esetén a kapcsoló egy konfigurált időtartamig ("manual_timeout") a manuális vezérlés szerint marad, utána automatikusan visszaáll, és az ekkor éppen aktuális ütemterv-célt követi. A `manual_timeout=0` speciális érték kivétel: ekkor nincs lejárati timer, a manuális állapot a következő ütemezett váltásig tart (lásd B2.4, B3.A).
```

**Futtatókörnyezet:** ☒ Custom integration ☐ Pyscript ☐ AppDaemon

## B2. Szótár

> Ez a gép **két független állapotgépből** áll (SPEC.md A4 elve szerint: "ha egymástól független dolgok futnak párhuzamosan → két külön állapotgép"): - **FŐ gép** — mi vezérli a kapcsolót: az ütemterv, vagy egy aktív manuális felülbírálás. (angolul: *main state machine*) - **ELERHETOSEGI gép** — a vezérelt entitás elérhető-e; tisztán diagnosztikai, NEM hat a FŐ gép működésére (failsafe elv). (angolul: *availability state machine*)

### B2.1 Állapotok — FŐ gép

| # | Állapot neve | Jelentés | Kezdőállapot? |
|---|---|---|---|
| 1 | `AUTO` | A kapcsolót az ütemterv aktuális `expected_state`-je vezérli; a poller aktívan szinkronban tartja a fizikai kapcsolóval. | ☒ |
| 2 | `MANUAL` | Manuális felülbírálás aktív (`manual_timeout` ideig, vagy — ha az 0 — a következő ütemezett váltásig); a fizikai kapcsoló a manuális beavatkozás szerinti állapotban marad, a poller nem nyúl hozzá. | ☐ |

### B2.1b Állapotok — ELERHETOSEGI gép (önálló, a FŐ géptől független)

| # | Állapot neve | Jelentés | Kezdőállapot? |
|---|---|---|---|
| 1 | `AVAILABLE` | A vezérelt entitás elérhető (nem `unavailable`/`unknown`). | ☐ |
| 2 | `UNAVAILABLE` | A vezérelt entitás `unavailable`/`unknown` — vagy ez a HA-indulás utáni kezdőállapot, amíg az első valós ellenőrzés meg nem erősíti az elérhetőséget. A FŐ gép ettől függetlenül, változatlanul tovább működik — csak diagnosztikai jelzés. | ☒ |

### B2.2 Események — FŐ gép

| # | Esemény neve | Forrás (entity / timer / szolgáltatás) |
|---|---|---|
| 1 | `schedule_on` | ütemterv (`on_crons` cron trigger) VAGY a `switch.<name>_timed_state` UI-kapcsolón / szabványos `switch.turn_on` szolgáltatással érkező külső BE parancs. Mindkét forrás mindig a `timed_state`-et frissíti; a külső parancs a következő tényleges cron-találatig marad érvényben. A hatás AUTO/MANUAL módban eltérő — lásd B3.A. |
| 2 | `schedule_off` | ugyanez KI irányban |
| 3 | `manual_change_on` | a kapcsolt eszközt tükröző entitások bármelyikének (`target_entity_id`, `switch.<name>_expected` VAGY `switch.<name>_device`) állapota BE-re változott, amit NEM a komponens saját service call-ja/írása és NEM az időzítő/ütemterv okozott (fizikai kapcsoló, HA-UI a `target_entity_id`-n, a `switch.<name>_expected` UI-kapcsoló, vagy a `switch.<name>_device` UI-kapcsoló — mind a négy egyenértékű bemenet). A `target_entity_id`-re vonatkozó megkülönböztetés mechanizmusa: lásd B3.3; a `switch.<name>_expected` és `switch.<name>_device` saját, komponens-implementálta entitások, itt nincs szükség ugyanerre a védelemre a saját kezelőjükön (lásd B2.3, B3.3). Bármelyik forrásból is jön, az esemény hatására `expected_state` a kiváltó iránynak megfelelő értékre áll (lásd B3.A). **Kizárás:** ha a `target_entity_id` state_changed eseményének RÉGI állapota `unavailable`/`unknown` volt (azaz az esemény egyben `became_available`-t is kivált — lásd B2.2b/#2, B3.B) — ez sosem minősül `manual_change_on/off`-nak; a `device_state` frissül, a `sensor.<name>_device_last_changed` pedig csak az előző ismert logikai értéktől való eltéréskor. A szinkronizálást a soron következő `state_sync` végzi el (AUTO módban). |
| 4 | `manual_change_off` | ugyanez KI irányban |
| 5 | `manual_timeout_expired` | belső timer, `manual_timeout` config paraméter szerint — csak akkor fordulhat elő, ha `manual_timeout > 0` (0 esetén nincs timer, lásd B2.4) |
| 6 | `override_cleared` | explicit felhasználói akció a felülbírálás azonnali megszüntetésére — szolgáltatásból, gombról, vagy a `switch.<name>_is_manual_mode` UI-kapcsoló kézi kikapcsolásából |
| 7 | `state_sync` | periodikus poller trigger, `sync_interval` config paraméter szerint — csak akkor fordulhat elő, ha `sync_interval > 0` (0 esetén a poller teljesen le van tiltva, lásd B2.4) |
| 8 | `override_set` | a `switch.<name>_is_manual_mode` UI-kapcsoló kézi bekapcsolása — explicit felhasználói akció a felülbírálás elindítására, a fizikai eszköz állapotának megváltoztatása/megkérdezése nélkül; `expected_state` és `timed_state` változatlan marad |

### B2.2b Események — ELERHETOSEGI gép

| # | Esemény neve | Forrás (entity / timer / szolgáltatás) |
|---|---|---|
| 1 | `became_unavailable` | a vezérelt entitás állapota `unavailable`/`unknown`-ra vált |
| 2 | `became_available` | a vezérelt entitás állapota visszaáll normál (`on`/`off`) értékre |

### B2.3 Entitások

| Szerep | entity_id | Típus | Megjegyzés |
|---|---|---|---|
| állapottároló | *(nincs input_select)* | saját futásidejű objektum (`Controller` osztály), `Store`-ban (`.storage` JSON) perzisztens | **Eltérés a CLAUDE.md alapértelmezésétől** — indoklás: custom integrationnél több entitás (switch, sensor, number) közös nézete egyetlen belső objektumra épül; input_select ide nem illő minta. Lásd A4-kiegészítés. |
| bemenet + kimenet | `target_entity_id` (tetszőleges domainű entity_id, pl. `switch.*`/`input_boolean.*`/`light.*`/`script.*`/`button.*`) | switch / input_boolean / light / script / button (felhasználó választása szerint) | a ténylegesen vezérelt entitás — egyszerre bemenet (manuális változás észlelése) és kimenet (domain-specifikus service call: turn_on/turn_off a switch/input_boolean/light/script domainnél, `button` domainnél mindig `press` — ld. B3.4). Kezdőértéke, ha a felhasználó nem ad meg sajátot: lásd `switch.<name>_virtual` sor. Élőben, reload nélkül átállítható más entitásra (lásd B2.4). |
| kimenet (UI, belső alapértelmezett cél) | `switch.<name>_virtual` | switch | Valódi, a komponens által létrehozott HA switch entitás (nem csak belső objektum) — úgy viselkedik, mintha fizikai eszköz lenne: kap service call-okat, van saját state-je. Ha a beállításkor nincs külső `target_entity_id` megadva, ez a `target_entity_id` kezdőértéke, hogy a FŐ gép fizikai eszköz nélkül is teljes körűen működjön/tesztelhető legyen. |
| bemenet + kimenet (UI) | `switch.<name>_expected` | switch | `Expected state` néven az `expected_state`-et mutatja és kézzel is állítja. AUTO módban élőben követi a `switch.<name>_timed_state`-et; MANUAL módban a kézi beavatkozás értékén fagyva marad (lásd B1, B3.A). Kézi kapcsolása `manual_change_on`/`manual_change_off` (lásd B2.2/#3-4). Saját, komponens-implementálta entitás — nincs önhivatkozási kockázat (lásd B3.3). Attribútum: `device_available` — a `target_entity_id` ELERHETOSEGI állapotát jelzi (lásd B2.1b); ettől függetlenül a kapcsoló vezérelhetősége változatlan marad (a beépített HA `unavailable` szürkítés itt szándékosan NEM használt, mert az letiltaná a vezérlést — lásd `binary_sensor.<name>_status` is). |
| bemenet + kimenet (UI) | `switch.<name>_timed_state` | switch | `Scheduled state` néven az ütemezés folyamatosan frissülő kimenetét mutatja — AUTO-ban és MANUAL-ban egyaránt frissül. Alapesetben a cron eredménye. UI-ból vagy külső automatizmus `switch.turn_on`/`switch.turn_off` hívásával átállítva időbélyegzett `schedule_on`/`schedule_off` eseményt vált ki; ez az érték a következő tényleges cron-találatig, cron nélkül korlátlan ideig érvényes, és HA-újraindítást is túlél. Saját, komponens-implementálta entitás, nincs önhivatkozási kockázat. Attribútumok: `next_schedule` (a következő cron-váltás abszolút időpontja) ISO 8601 transport formátumban; `external_schedule_active` jelzi a külső ütemezési parancs aktív voltát. |
| bemenet + kimenet (UI) | `switch.<name>_is_manual_mode` | switch | A FŐ gép állapotát mutatja és kézzel is váltja: `is_on=True` ⇒ manuális mód (`MANUAL`), `is_on=False` ⇒ időzített mód (`AUTO`). Kézi bekapcsolása `override_set`, kikapcsolása `override_cleared` (lásd B2.2/#6, #8). Saját, komponens-implementálta entitás — nincs szüksége context-echo védelemre. |
| bemenet + kimenet (UI) | `switch.<name>_device` | switch | `Device state` néven a `target_entity_id` kétirányú tükre: bármelyik irányból (itt vagy közvetlenül a `target_entity_id`-n) történő váltás egyenértékű. Kézi (nem a komponens saját service call-ja miatti) váltása `manual_change_on`/`manual_change_off` eseményt vált ki, ugyanúgy mintha közvetlenül a `target_entity_id`-t kapcsolták volna át (lásd B2.2/#3-4, B3.3 kiterjesztett hatóköre). Elérhetőség: a `target_entity_id` ELERHETOSEGI állapotát tükrözi. |
| kimenet (UI) | `binary_sensor.<name>_status` | binary_sensor (`device_class: problem`) | `Status` néven ON, ha az ELERHETOSEGI gép `UNAVAILABLE` állapotban van (B2.1b) — feltűnő, alapértelmezett HA-jelzés (a legtöbb beépített kártyán/area-nézeten konfiguráció nélkül is látszik), kiegészítve a `switch.<name>_expected` `device_available` attribútumát. |
| kimenet (API + UI-forrás) | `sensor.<name>_manual_remaining` | sensor (`device_class: timestamp`, stabil abszolút céldátum) | `Time Until Override` néven, a Diagnostic blokkban jelenik meg. MANUAL módban a `manual_timeout` céldátuma; `manual_timeout=0` esetén nincs értelmezve. A Timed Switch Card ebből böngészőoldalon számolja és változatlan `óó:pp:ss` formában másodpercenként frissíti a hátralévő időt, ezért a visszaszámlálás nem generál másodpercenkénti HA state-változást. |
| kimenet (API + UI-forrás) | `sensor.<name>_sync_remaining` | sensor (`device_class: timestamp`, stabil abszolút céldátum) | `Time Until Sync` néven, a Diagnostic blokkban jelenik meg. A következő `state_sync` céldátuma; `sync_interval=0` esetén nincs értelmezve. A Timed Switch Card ebből böngészőoldalon számolja és változatlan `óó:pp:ss` formában másodpercenként frissíti a hátralévő időt, ezért a visszaszámlálás nem generál másodpercenkénti HA state-változást. |
| kimenet (UI) | `sensor.<name>_since_last_change` | sensor (`device_class: timestamp`) | `Since Expected Change` néven az `expected_state` utolsó tényleges értékváltásának ABSZOLÚT időpontja. Csak az időpont van tárolva — a „mennyi ideje” relatív megjelenítés a HA frontend natív timestamp-renderelése, nincs külön számolva/tárolva. |
| kimenet (UI) | `sensor.<name>_device_last_changed` | sensor (`device_class: timestamp`) | `Since Device Change` néven a tükrözött logikai `device_state` utolsó tényleges ON/OFF értékváltásának abszolút időpontja. Azonos állapotú, csak attribútumot módosító `state_changed` esemény és az elérhetőség változása nem írja felül. |
| kimenet (UI) | `sensor.<name>_timed_state_last_changed` | sensor (`device_class: timestamp`) | `Since Timed State Change` néven a `timed_state` utolsó tényleges értékváltásának abszolút időpontja. Azonos értéket adó ismételt cron- vagy külső parancs nem írja felül. |
| kimenet (UI) | `text.<name>_target_entity` | text | `Target entity` néven, a Configuration blokkban megjeleníti az adott Timed Switch által ténylegesen vezérelt `target_entity_id` értékét. A mező csak olvasható; eltérő érték beállítását visszautasítja. |
| kimenet (UI) | `number.<name>_manual_timeout` | number (mp) | A `manual_timeout` perzisztens beállítása; a number entitáson módosított érték HA-újraindítás után is megmarad. |
| kimenet (UI) | `number.<name>_sync_interval` | number (mp) | A `sync_interval` perzisztens beállítása; a number entitáson módosított érték HA-újraindítás után is megmarad. `0` = a poller (`state_sync`) teljesen kikapcsolva (lásd B2.4). |
| bemenet + kimenet (UI) | `text.<name>_on_crons` | text | `Schedule ON` néven az ON cron-lista élő szerkesztése. |
| bemenet + kimenet (UI) | `text.<name>_off_crons` | text | `Schedule OFF` néven az OFF cron-lista élő szerkesztése. |

**Device-csoportosítás:** a fenti táblázat összes entitása (a `target_entity_id` kivételével, ami külső entitás) egyetlen közös HA Device alá tartozik, komponens-példányonként egy Device (azonosító: `(DOMAIN, entry_id)`). Enélkül az entitások a HA UI-n szórt, kontextus nélküli listaelemekként jelennek meg, nem egy áttekinthető eszközkártyaként — ez a felhasználói felület szempontjából ugyanolyan kötelező elem, mint bármelyik fenti sor.

**Entity-category (elsődleges vs. másodlagos entitás):** a Device az összetartozást biztosítja, az `entity_category` pedig kizárólag a HA eszközoldalán történő helyes szétválogatást. Vezérlő vagy normál működési állapotot mutató entitás nem lehet `diagnostic`, mert akkor a HA elrejti az automatikus dashboard-ajánlásokból.

- elsődleges (nincs `entity_category`) — `switch.<name>_expected`, `switch.<name>_timed_state`, `switch.<name>_device`, `switch.<name>_is_manual_mode`, valamint `switch.<name>_virtual`, ha létrejön;
- `entity_category: config` — `text.<name>_target_entity`, `number.<name>_manual_timeout`, `number.<name>_sync_interval` és a két cron-lista `text` entitása;
- `entity_category: diagnostic` — `binary_sensor.<name>_status`, `sensor.<name>_manual_remaining`, `sensor.<name>_sync_remaining`, `sensor.<name>_since_last_change`, `sensor.<name>_device_last_changed`, `sensor.<name>_timed_state_last_changed`.

### B2.3a Dashboard-kártya

Az integráció saját, egyetlen dashboard-elemként hozzáadható `custom:timed-switch-card` kártyát szállít. A kártya nem tartalmaz új állapotlogikát, hanem a B2.3 entitásainak egységes nézete és kezelőfelülete.

- Kötelező konfigurációja egyetlen `entity`: a példány `switch.<name>_expected` entitása.
- A többi entitást a rögzített B2.3 entity_id-szuffixumok alapján automatikusan azonosítja; ezeket a felhasználónak nem kell egyenként megadnia.
- Egy kártya pontosan egy Timed Switch config entryt / Device-ot jelenít meg.
- Egy vizuális blokkban mutatja legalább: fő célállapot, AUTO/MANUAL mód, nyers ütemezett állapot, fizikai eszközállapot (ha értelmezett), manuális hátralévő idő, timeout, ellenőrzési időköz, következő ütemezés és hibajelzés.
- Minden vezérlés a meglévő entitások szabványos HA service call-ját használja.
- Hiányzó vagy letiltott másodlagos entitásnál a működő részek használhatók maradnak, a hiányzó adat helyén `—` jelenik meg.
- A kártya mobilon és asztali nézetben is egyetlen reszponzív kártya marad.
- A kártya belső megjelenítése a HA beépített `entities` kártyáját és natív entity-row vezérlőit használja; saját ON/OFF gombot, number inputot, dátumformázót vagy párhuzamos vizuális komponenst nem implementál. Így a kapcsolók, számmezők, tipográfia, térközök, témák és timestamp-formátumok a HA többi komponensével azonosak. A két hátralévőidő-sor a backend stabil timestamp céldátumából, kizárólag a böngészőben számolja ki a megjelenített `óó:pp:ss` értéket; az egy másodperces UI-frissítés nem ír HA-entitásállapotot és nem hoz létre state-változási eseményt. A többi timestamp sor rövid, numerikus `datetime/short` megjelenítést használ, nem hosszú, hónapnevet kiíró szöveges dátumot. A Sections grid számára csak az oszlopszélességet adja meg; fix `rows`/`min_rows` magasságot nem állít be, ezért a kártya a teljes entitáslistához igazodik, nem vágja le és nem teszi belsőleg görgethetővé a tartalmat.
- A JavaScript-modult az integráció saját statikus URL-en szolgálja ki és verziózott Lovelace resource-ként automatikusan regisztrálja; kézi fájlmásolás/resource-felvétel nem kell, és integrációfrissítéskor a böngésző nem tarthatja meg a régi kártyakódot.
- A kártya regisztrálja magát a HA kártyaválasztójában (`window.customCards`), és HA 2026.6+-on `getEntitySuggestion` segítségével a Timed Switch fő entitásához ajánlja fel magát. Így UI-ból, YAML írása nélkül, egyetlen kártyaként adható a dashboardhoz.

### B2.4 Időzítők / paraméterek

A konfigurációs és dashboard-UI cron mezők minden kifejezést öt mezőre normalizálnak. A hiányzó mezőket jobb oldalon `*` értékekkel egészítik ki. Az ötödik utáni mezőket csak akkor dobják el, ha mind `*`; más többletmező a meglévő cron-validációs hibát eredményezi.

| Név | Érték | Jelentés |
|---|---|---|
| `on_crons` / `off_crons` | felhasználó adja meg — cron-szerű kifejezések listája, soronként vagy vesszővel elválasztva, `#` a komment, `croniter` szintaxis, perc-pontosság | Külön ON és OFF cron-lista (nem egy kombinált tábla). **Élőben (reload nélkül) szerkeszthető** az options flow-n keresztül. A cron-kiértékelés külső ütemezési parancs alatt is minden perc pontos kezdetén fut és frissíti a `next_schedule`-t. A ticker monotón késleltetéssel ébred, minden ébredéskor az aktuális helyi falórából újraszámolja a következő percfordulóig tartó késleltetést, és a következő ébredést a cronértékelés előtt regisztrálja. Emiatt előre vagy visszafelé történő rendszeróra-ugrás, illetve egy kiértékelési hiba sem állíthatja le tartósan: legfeljebb egy 60 másodperces monotón intervallumon belül újraigazodik. A következő tényleges ON vagy OFF cron-találat megszünteti a külső parancs elsőbbségét. Ha mindkét lista üres, nincs automatikus cron-váltás: külső parancs hiányában a `timed_state` a `default_state` értéken marad, aktív külső parancs pedig korlátlan ideig érvényes; `next_schedule` értelmezhetetlen (`—`). A cronmotor független a `sync_interval`-tól. **A cron-kifejezéseket a HA-ban konfigurált HELYI időzónában értelmezzük** (nem UTC-ben) — pl. `0 8 * * *` a felhasználó helyi 8:00-ját jelenti. |
| `manual_timeout` | felhasználó adja meg (mp), alapértelmezett **600** | Mennyi ideig érvényes egy manuális felülbírálás, mielőtt automatikusan visszaáll az ütemtervre. **Speciális eset: `manual_timeout=0`** → nincs lejárati timer; a `MANUAL` állapot a következő `schedule_on`/`schedule_off` eseményig tart (lásd B3.A). Futásidőben felülbírálható a `number.<name>_manual_timeout` entitással, függetlenül a config alapértéktől. **Élő módosítás hatálya:** ha épp fut egy MANUAL visszaszámlálás, az új érték csak a KÖVETKŐ manuális belépéskor/timer-újraindításkor (B3.1/B3.A) érvényesül — a már elindított timert nem írja felül azonnal. |
| `sync_interval` | felhasználó adja meg (mp), alapértelmezett **60** | A poller (`state_sync`) periódusideje. **Speciális eset: `sync_interval=0`** → a poller teljesen kikapcsolva, `state_sync` esemény soha nem generálódik, amíg vissza nem áll `>0` értékre. Futásidőben felülbírálható a `number.<name>_sync_interval` entitással. **Élő módosítás hatálya:** ezzel szemben **azonnal** újraindítja a pollert az új intervallummal (aszimmetria a `manual_timeout` élő módosításához képest — szándékos: a poller egy önálló, folyamatos ciklus, nincs "aktuális futása", amit ne lehetne azonnal újraindítani). |
| `default_state` | felhasználó adja meg (BE/KI) | A kapcsoló kezdő értéke, ha nincs érvényes mentett állapot és/vagy még nincs kiértékelhető ütemterv. |
| `notify_events` | felhasználó adja meg (bool), alapértelmezett **false** | Ha igaz, HA `persistent_notification` jön létre ütemezett célváltáskor és enforce-akciónál — lásd B4/10. |

### B2.4a Célkapcsoló kiválasztása a config flow-ban

A Timed Switch létrehozása teljesen UI-vezérelt, és a cél kiválasztása külön lépésben történik. A meglévő állapotgép és a `target_entity_id` jelentése nem változik; kizárólag annak UI-beli meghatározási módja bővül.

| Választás | Elérhetőség | Eredmény |
|---|---|---|
| `built_in_virtual` | mindig | A jelenlegi `switch.<name>_virtual` jön létre és lesz a `target_entity_id`. Ez a jelenlegi alapértelmezett működés változatlanul megmarad. |
| `existing_entity` | mindig | A felhasználó a támogatott domainek meglévő entitásai közül választ; meglévő Virtual Switch esetén annak `switch.<virtual_name>_main` entitását választja. |
| `new_virtual_switch` | csak akkor, ha a `virtual_switch` integráció telepítve és betölthető | A UI új Virtual Switch létrehozását indítja, majd annak `switch.<virtual_name>_main` entitása lesz a `target_entity_id`. |

További kötelező szabályok:

- A Virtual Switch opcionális együttműködés: hiánya nem akadályozhatja a Timed Switch telepítését, betöltését, frissítését vagy meglévő config entryinek működését.
- Ha a `virtual_switch` nincs jelen, a `new_virtual_switch` választás nem jelenik meg; nem jelenhet meg működésképtelen menüpont.
- Az `existing_entity` selector a támogatott domaineket továbbra is felajánlja. Ha a Virtual Switch jelen van, annak `*_main` kapcsolói normál `switch` célként választhatók.
- Új Virtual Switch létrehozását a `virtual_switch` saját config flow-ja végzi. A TimedSwitch nem másolja és nem birtokolja annak állapotgépét.
- A létrehozott Virtual Switch önálló config entry és Device marad. Törlése, átnevezése és állapot-perzisztenciája a `virtual_switch` integráció felelőssége.
- A TimedSwitch a kapcsolódás után kizárólag szabványos HA switch service callokon és state change eseményeken keresztül használja a Virtual Switch `main` entitását, ugyanúgy, mint bármely más külső `switch` célt.
- Ha az új Virtual Switch létrehozását a felhasználó megszakítja vagy az sikertelen, a Timed Switch config flow visszatér a célválasztáshoz, és nem hoz létre félkész entryt.
- Timed Switch törlése nem törölheti a hozzá kapcsolt Virtual Switch entryt vagy Device-ot.

## B3. Átmeneti tábla

> **MINDEN cella kötelező.** Ahol nincs teendő, írd: `— (ignore)`. Formátum egy cellában: `CÉLÁLLAPOT [guard] → akció`

### B3.A — FŐ gép

| Állapot \ Esemény | `schedule_on` | `schedule_off` | `manual_change_on` | `manual_change_off` | `manual_timeout_expired` | `override_cleared` | `override_set` | `state_sync` |
|---|---|---|---|---|---|---|---|---|
| `AUTO` | marad `AUTO` → `timed_state`=BE; `expected_state`=BE (követi `timed_state`-et); `[guard: device_state != expected_state]` → kapcsoló BE | marad `AUTO` → `timed_state`=KI; `expected_state`=KI; `[guard: device_state != expected_state]` → kapcsoló KI | `MANUAL` → `expected_state`=BE (a kézi beavatkozás szerint) (lásd B3.1 entry akció) | `MANUAL` → ugyanaz, mint a `manual_change_on` cellában, KI irányban | — (ignore, nincs aktív felülbírálás) | — (ignore, nincs aktív felülbírálás) | `MANUAL` (lásd B3.1 entry akció); `expected_state` és `timed_state` változatlan | marad `AUTO` `[guard: device_state != expected_state]` → kapcsoló beállítása `expected_state` szerint |
| `MANUAL` | `timed_state`=BE (a háttérben; `expected_state` és a fizikai kapcsoló **változatlan**); `[guard: manual_timeout == 0]` → `AUTO` (lásd B3.1 entry akció, ami a pillanatnyi `timed_state`-et alkalmazza); egyébként marad `MANUAL` | `timed_state`=KI (a háttérben; `expected_state` és a fizikai kapcsoló **változatlan**); `[guard: manual_timeout == 0]` → `AUTO` (lásd B3.1 entry akció); egyébként marad `MANUAL` | marad `MANUAL` → `expected_state`=BE (a kézi beavatkozás szerint); `[guard: manual_timeout > 0]` timer újraindítása (`manual_timeout`); `[guard: manual_timeout == 0]` nincs timer | marad `MANUAL` → ugyanaz, mint a `manual_change_on` cellában, KI irányban | `AUTO` (lásd B3.1 entry akció). Csak `manual_timeout > 0` esetén fordulhat elő. | `AUTO` (lásd B3.1 entry akció) | — (ignore, már `MANUAL`; a `switch.<name>_is_manual_mode` már be van kapcsolva, HA nem tüzel ismételt azonos értékre) | — (ignore, felülbírálás alatt a poller nem avatkozik be) |

### B3.B — ELERHETOSEGI gép (a FŐ géptől független)

| Állapot \ Esemény | `became_unavailable` | `became_available` |
|---|---|---|
| `AVAILABLE` | `UNAVAILABLE` → naplózás, diagnosztikai jelzés bekapcsolása | — (ignore) |
| `UNAVAILABLE` | — (ignore) | `AVAILABLE` → naplózás, diagnosztikai jelzés törlése |

### B3.1 Entry / exit akciók — FŐ gép

| Állapot | Belépéskor (entry) | Kilépéskor (exit) |
|---|---|---|
| `AUTO` | `expected_state` := pillanatnyi `timed_state`; `[guard: device_state != expected_state]` → kapcsoló beállítása `expected_state` szerint | — (ignore) |
| `MANUAL` | `[guard: manual_timeout > 0]` → timer indítása (`manual_timeout`); `[guard: manual_timeout == 0]` → nincs timer, a visszatérés a következő `schedule_on`/`schedule_off` eseménytől függ (lásd B3.A). (`expected_state`-et a belépést kiváltó `manual_change_on/off` esemény már beállította — lásd B3.A.) | timer törlése, ha még aktív |

### B3.2 Induláskor / HA-újraindítás után (nem táblacella, külön eljárás)

```
1. Store-ból betöltjük a mentett Controller-állapotot: state (AUTO/MANUAL), expected_state (csak MANUAL esetén releváns, a fagyasztott kézi érték), manual_until lejáratának ABSZOLÚT időpontja, valamint az utolsó külső ütemezési parancs értéke és ABSZOLÚT időpontja.
2. Ha nincs mentett adat vagy érvénytelen: state = AUTO, expected_state = default_state.
3. Frissen kiszámoljuk a cron szerinti `timed_state`-et, a legutóbbi cron-találatot és a `next_schedule` attribútumot. Ha a mentett külső ütemezési parancs újabb a legutóbbi cron-találatnál, annak értéke lesz a `timed_state`; ellenkező esetben a cron eredménye nyer és a külső parancs törlődik. Ezáltal a HA-kiesés alatt bekövetkezett cron-találat is helyesen visszaveszi a vezérlést.
4. Ha a mentett állapot **AUTO** volt: `expected_state` := a frissen számolt `timed_state`; a B3.1 AUTO entry akció elvégzi a kapcsoló szinkronizálását.
5. Ha a mentett állapot **MANUAL** volt, és a mentett lejárati időpont már elmúlt a kiesés alatt (csak manual_timeout > 0 esetén értelmezhető): → AUTO-ra lépünk; `expected_state` := a frissen számolt `timed_state`; a B3.1 entry akció elvégzi a kapcsoló beállítását.
6. Ha a mentett állapot MANUAL volt, manual_timeout == 0 (nincs lejárati időpont): → MANUAL marad; `expected_state` a mentett (fagyasztott) értéken marad; a visszatérés továbbra is a következő schedule_on/schedule_off eseménytől függ.
7. Egyébként (MANUAL és a lejárat még nem múlt el): → MANUAL marad, `expected_state` a mentett (fagyasztott) értéken marad, a timer a mentett abszolút lejárati időponttal folytatódik.
8. Az ELERHETOSEGI gép mindig `UNAVAILABLE`-lel indul (nem perzisztált, lásd B2.1b), és az első valós `target_entity_id` állapot-lekérdezéskor azonnal átvált `AVAILABLE`-re, ha az elérhető.
```

### B3.3 Önhivatkozás elleni védelem (echo-suppression)

```
Amikor a komponens saját maga hív service call-t a target_entity_id domainjének megfelelő szolgáltatással (switch/input_boolean/light/script domainnél turn_on/turn_off, button domainnél press — ld. B3.4) a target_entity_id-re — az AUTO állapot entry/state_sync korrekciója, a MANUAL→AUTO átmenet szinkronizációja, vagy a switch.<name>_expected-ről / switch.<name>_device-ról érkező manual_change_on/off esemény kapcsán a target_entity_id-re történő irány-szinkronizáció során — az ebből eredő state_changed esemény NEM minősül manual_change_on/off eseménynek. Button célnál ez a mechanizmus nem releváns, mivel arra a domainre nincs state_changed-alapú megfigyelés (ld. B3.4).

Mechanizmus: a service call meghívásakor visszakapott HA `Context` objektum `id`-ját eltároljuk (`_last_own_context_id`). A target_entity_id state_changed eseményének feldolgozásakor a `new_state.context.id`-t ezzel összevetjük:
  - ha egyezik → a változást a komponens okozta, az eseményt eldobjuk (nem generálunk belőle manual_change_* eseményt, de a `device_state` frissül; a `sensor.<name>_device_last_changed` csak tényleges ON/OFF értékváltáskor frissül);
  - ha nem egyezik → valódi manual_change_on/off esemény.

Ez a megoldás HA-context-lánccal, race condition nélkül működik, és nem igényel időzítés-függő "várakozás" állapotot.

**Hatókör:** ez a mechanizmus kizárólag a target_entity_id-re vonatkozik, mert az egy külső, a komponens által nem birtokolt entitás, amit passzívan, state_changed-eseményen keresztül figyelünk. A switch.<name>_expected, switch.<name>_device, switch.<name>_timed_state és switch.<name>_is_manual_mode ezzel szemben a komponens SAJÁT, általa implementált entitásai (lásd B2.3): ezek turn_on/turn_off handlere maga a komponens kódja, a komponens a saját attribútumfrissítéseiket közvetlenül (`async_write_ha_state()`) végzi, nem service call-on és nem state_changed-figyelésen keresztül — emiatt itt nincs önhivatkozási kockázat, minden rájuk érkező turn_on/turn_off hívás definíció szerint külső (felhasználói/automatizálási) parancs. A switch.<name>_device saját handlere ráadásul TOVÁBB is hív egy service call-t a target_entity_id-re (hogy a fizikai eszközön is érvényesüljön a váltás) — ennek a továbbított hívásnak az eredményeként a target_entity_id-n keletkező state_changed esemény a fenti context-echo mechanizmus szerint elnyelődik, ugyanúgy, mint a switch.<name>_expected esetén (lásd T12 mintájára).
```

### B3.4 `button` domain speciális szabálya (nincs megfigyelhető device_state)

```
A HA `button` domainnek nincs `on`/`off` állapota — csak egy "utoljára megnyomva" időbélyeg. Emiatt a target_entity_id `button` domain esetén nem viselkedik kétállapotú eszközként, hanem egyetlen, toggle-jellegű kimenetként:

1. Szolgáltatáshívás: mindig `button.press`, irányfüggetlenül. Nincs `expected_state`-hez rendelt "BE szolgáltatás" / "KI szolgáltatás" pár — a `press` maga a váltás.
2. Kiváltó feltétel: a B3.A táblában szereplő minden akció, ami más domainnél "kapcsoló BE" / "kapcsoló KI" service callt jelentene, button célnál egységesen egyetlen `press`-t jelent, DE csak akkor, ha az `expected_state` ténylegesen VÁLTOZOTT (schedule_on/schedule_off esemény más irányú célt állít be, mint az aktuális expected_state). Változatlan irányú ismételt esemény (pl. két egymást követő schedule_on ugyanarra az irányra) nem nyom újra — ez az idempotencia elve (lásd CLAUDE.md 3.).
3. `device_state` fogalma nem értelmezett: nincs mivel összevetni az `expected_state`-et. Ebből következik:
   - a `state_sync` (poller) button célnál mindig no-op — nincs mit ellenőrizni/enforce-olni;
   - a B3.A táblában szereplő `[guard: device_state != expected_state]` guardok button célnál úgy értendők, mintha `device_state` mindig ismeretlen (`None`) lenne — vagyis csak az `expected_state` tényleges változása vált ki akciót, sosem a poller.
4. Manuális változás detektálása button célnál **nem lehetséges**: mivel nincs megfigyelhető állapot, a `manual_change_on`/`manual_change_off` esemény button target esetén soha nem generálódik. A MANUAL mód button célnál csak a `switch.<name>_is_manual_mode` UI-kapcsolón keresztül, explicit módon érhető el, fizikai gombnyomásból soha.
5. Az ELERHETOSEGI gép (B2.1b) button célnál is működik: a `button` entitásnak van `available`/`unavailable` állapota, ez független a fenti 4. ponttól.
6. **Nyitott kérdés:** a `switch.<name>_device` (B2.3) mint a `target_entity_id` kétirányú tükre `button` célnál nem értelmezhető közvetlenül (nincs mit tükrözni, nincs on/off állapot) — pontos viselkedése (létrejön-e egyáltalán, és ha igen, mit jelent a kézi átbillentése) button célnál még nincs eldöntve, lásd B6.
```

## B4. Peremfeltétel-kérdőív

> Ezek a kérdések nem hagyhatók ki. Mindegyikre konkrét válasz kell.

| # | Kérdés | Válasz |
|---|---|---|
| 1 | HA-újraindítás után melyik állapotba kerülünk? (mentett / fix alaphelyzet / feltételes) | Mentett állapot + a perzisztens, előre kiszámolt abszolút időpontok alapján újraszámolt legfrissebb érvényes állapot — a kiesés "mintha meg sem történt volna". Részletes eljárás: B3.2. |
| 2 | Ha a mentett állapot érvénytelen vagy hiányzik? | `AUTO`, `expected_state` = `default_state` (config paraméter). |
| 3 | Mi történik, ha egy bemeneti szenzor `unavailable`? | A FŐ gép változatlanul, virtuálisan tovább működik. Az ELERHETOSEGI gép `UNAVAILABLE`-ba lép, diagnosztikai jelzés. A service call-ok naplózott hibával térhetnek vissza, de a normál működés (poller, ütemterv) folytatódik — lásd B4/12. |
| 4 | Mi történik, ha egy bemeneti szenzor `unknown`? | Ugyanúgy kezelendő, mint az `unavailable` (ugyanaz a `became_unavailable` esemény váltja ki); a manuális-változás-detektáló logika is egyformán, figyelmen kívül hagyva kezeli mindkettőt. |
| 5 | Az időzítők túlélik a restartot? Ha igen, hogyan? | Igen — `Store`-ban (`.storage` JSON), ABSZOLÚT időpontokkal tárolva (nem hátralévő időtartammal). |
| 6 | Ha egy timer lejár, de közben már más állapotban vagyunk? | Nem releváns így: a FŐ gép minden eseményt fogad guarddal, nincs blokkoló "más állapot" jellegű átfedés. |
| 7 | Egyszerre érkező eseményeknél mi a prioritási sorrend? | FIFO — érkezési sorrend, a HA event loop természetes sorrendjében, nincs kitüntetett prioritás. |
| 8 | Idempotens-e minden akció? (kétszer jövő esemény → egyszer fut?) | Igen — a CLAUDE.md 3. szabálya kötelezővé teszi. Pl. a `state_sync` és a `schedule_on/off` cellák is guardolva vannak (`device_state != expected_state`), hogy felesleges service call ne fusson kétszer. |
| 9 | Van olyan átmenet, amit ember kézzel is kiválthat a UI-ról? | Igen, mindkét irányban. MANUAL-ba lépés kézzel: a `target_entity_id`, a `switch.<name>_expected` vagy a `switch.<name>_device` átkapcsolásával (`manual_change_on/off`), vagy a `switch.<name>_is_manual_mode` bekapcsolásával (`override_set`). AUTO-ra visszaállás: automatikusan (`manual_timeout_expired`) VAGY explicit manuálisan (`override_cleared` — szolgáltatásból, gombról, vagy a `switch.<name>_is_manual_mode` kikapcsolásával). Emellett a `switch.<name>_timed_state` kézi átbillentése is UI-ból kiváltható, valódi `schedule_on/off` eseményként (teszt célra — lásd B2.2/#1-2). |
| 10 | Naplózás: melyik átmeneteket kell logolni / értesítést küldeni? | Minden állapotátmenet naplózva (CLAUDE.md 3. szabálya szerint kötelező: honnan → hova, kiváltó esemény, időbélyeg). HA-értesítés (`persistent_notification`): opcionális, a `notify_events` config paraméter kapcsolja be/ki, ütemezett célváltáskor és enforce-akciónál küld (lásd B2.4). |
| 11 | Van "vészleállító" / bypass állapot? | Nincs külön, explicit BYPASS állapot ebben a körben. Helyette a `manual_timeout=0` paraméterérték a meglévő `MANUAL` állapotban engedi, hogy a felülbírálás időzítő nélkül maradjon aktív, és csak a következő `schedule_on`/`schedule_off` esemény zárja le (lásd B2.4, B3.A). Egy teljes, explicit "amíg vissza nem kapcsolom" BYPASS mód (saját állapottal, saját szolgáltatással, a schedule-tól is függetlenül) továbbra sem témája ennek a körnek — lásd B6. |
| 12 | Mi legyen, ha egy akció (service call) hibára fut? | Naplózás + hibajelzés, nincs külön retry-állapotgép/logika. A normál működés (a soron következő `state_sync` vagy `schedule_on/off` esemény) magától újra megpróbálja — ez a "failsafe" elv, amit a poller biztosít. |
| 13 | Hogyan különböztetjük meg a komponens saját service call-ja okozta állapotváltást a valódi manuális beavatkozástól? | HA `Context.id` összevetés a service call és a state_changed esemény között. Részletes mechanizmus: B3.3. |
| 14 | Mi történik `button` domainű cél entitásnál, aminek nincs `on`/`off` állapota? | Minden `expected_state`-váltás (mindkét irányban) egyetlen `button.press` hívást jelent, `device_state` összevetés nélkül; a `state_sync` poller button célnál no-op; fizikai/UI gombnyomás sosem generál `manual_change_on/off` eseményt (nincs megfigyelhető állapot). Részletes szabály: B3.4. |
| 15 | Mi történik, ha a `target_entity_id` `unavailable`/`unknown`-ból visszatér egy konkrét `on`/`off` állapottal (pl. áramkimaradás után megjegyzett állapot)? | Ez NEM minősül manuális beavatkozásnak — a `became_available`-lel egybeeső state_changed kizárva a `manual_change_on/off` eseményből (lásd B2.2/#3-4, B3.B). Nincs azonnali kényszerített akció; AUTO módban a soron következő `state_sync` szinkronizálja a fizikai kapcsolót az `expected_state`-tel. **Következmény:** ha `sync_interval=0` (poller kikapcsolva), egy visszakapcsolódáskori eltérés javítatlan marad, amíg a `sync_interval` vissza nem áll `>0`-ra. |
| 16 | Mi történik a perzisztált állapottal (B3.2 Store), ha a felhasználó törli az integráció-példányt (nem csak kikapcsolja/reload-olja)? | A perzisztált Store JSON-t explicit törölni kell integráció-törléskor — HA az entitás-/eszközregisztrációt automatikusan takarítja, de a komponens saját Store-fájlját nem. Nem maradhat árva mentett állapot a lemezen egy már nem létező config entry-hez. |

## B5. Elfogadási tesztek

> Ezeket az AI generálja a B3 táblából, **de te hagyod jóvá kód előtt.** Formátum: kezdőállapot → eseménysor → várt végállapot + várt akciók.

### FŐ gép

| # | Kezdőállapot | Eseménysor | Várt végállapot | Várt akciók |
|---|---|---|---|---|
| T1 | `AUTO` (device_state=KI, expected_state=KI) | `schedule_on` | `AUTO` | `expected_state`=BE; kapcsoló BE (service call) |
| T2 | `AUTO` (device_state=BE, expected_state=BE) | `manual_change_off` | `MANUAL` | `manual_timeout>0`: timer indul (`manual_timeout`); nincs extra service call |
| T3 | `MANUAL` (expected_state=KI, manual_timeout>0) | `manual_timeout_expired` | `AUTO` | kapcsoló beállítása `expected_state` (KI) szerint |
| T4 | `MANUAL` (device_state=KI, felülírás miatt) | `schedule_on` | `MANUAL` (változatlan) | `timed_state`=BE frissül a háttérben; `expected_state` és a fizikai kapcsoló **változatlan** (KI) |
| T5 | `AUTO` (device_state=KI, expected_state=BE — pl. korábban elveszett service call miatt eltért) | `state_sync` | `AUTO` (változatlan) | kapcsoló BE (korrekciós service call) |
| T6 | `MANUAL` (expected_state=BE) | `override_cleared` | `AUTO` | kapcsoló beállítása `expected_state` (BE) szerint |
| T7 | Induláskor: mentett `MANUAL`, mentett lejárati időpont **már elmúlt** a HA-kiesés alatt (manual_timeout>0) | *(betöltés / újraindítás)* | `AUTO` | kapcsoló beállítása `expected_state` szerint |
| T8 | `MANUAL` (manual_timeout=0, expected_state=KI) | `manual_change_on` (ismételt kézi kapcsolgatás) | `MANUAL` (változatlan) | `expected_state`=BE (a kézi irány szerint frissül); nincs timer-esemény soha; a `MANUAL`-ból való kilépés csak `schedule_on`/`schedule_off`-ra (azaz `timed_state`-mozgásra) vár |
| T9 | `MANUAL` (manual_timeout=0, expected_state=KI) | `schedule_on` | `AUTO` | `timed_state`=BE; belépéskor `expected_state`=BE (a pillanatnyi `timed_state`-ből); kapcsoló BE — a 0-timeout override így zárul le |
| T10 | `AUTO` (device_state=KI, expected_state=KI) | `state_sync` → (a poller saját service call-ja BE-re állítja a device_state-et, ugyanazzal a HA Context-tel) | `AUTO` (nem `MANUAL`!) | a saját service call miatti state_changed esemény **nem** generál `manual_change_on` eseményt (lásd B3.3) |
| T11 | `AUTO` (device_state=KI, expected_state=KI) | `override_set` (forrás: `switch.<name>_is_manual_mode` kézi bekapcsolása) | `MANUAL` | timer indul (`manual_timeout`); `expected_state` változatlan (KI); **nincs** service call (a fizikai eszköz már ott áll, ahol `expected_state`) |
| T12 | `AUTO` (device_state=KI, expected_state=KI) | `manual_change_on` (forrás: `switch.<name>_expected` kézi bekapcsolása) | `MANUAL` | `expected_state`=BE; timer indul (`manual_timeout`); kapcsoló BE (service call a `target_entity_id`-re, hogy kövesse az új célt) — a keletkező state_changed a B3.3 kiterjesztett hatóköre miatt (saját context) **nem** generál újabb `manual_change_on` eseményt |
| T17 | `AUTO` (device_state=KI, expected_state=KI, timed_state=KI) | `switch.<name>_timed_state` kézi átbillentése BE-re | `AUTO` (változatlan) | ugyanaz, mint T1: `timed_state`=BE (valódi `schedule_on` eseményt vált ki); `expected_state`=BE; kapcsoló BE |
| T18 | `MANUAL` (device_state=KI, expected_state=KI, manual_timeout>0) | `switch.<name>_timed_state` kézi átbillentése BE-re | `MANUAL` (változatlan) | ugyanaz, mint T4: `timed_state`=BE a háttérben; `expected_state` és a fizikai kapcsoló **változatlan** |
| T19 | `AUTO` (device_state=KI, expected_state=KI) | `manual_change_on` (forrás: `switch.<name>_device` kézi bekapcsolása) | `MANUAL` | `expected_state`=BE; timer indul (`manual_timeout`); kapcsoló BE (a `switch.<name>_device` handlere továbbítja a service call-t a `target_entity_id`-re) — a keletkező state_changed a B3.3 kiterjesztett hatóköre miatt **nem** generál újabb `manual_change_on` eseményt |
| T20 | `AUTO`, `sync_interval=0` | *(idő telik, nincs esemény)* | `AUTO` (változatlan) | `state_sync` esemény **soha nem** generálódik, amíg `sync_interval` vissza nem áll `>0`-ra — a poller ki van kapcsolva |
| T21 | `AUTO` (expected_state=BE); `target_entity_id` `unavailable` volt, most visszatér `off` állapottal | *(target_entity_id state_changed: `unavailable` → `off`)* | `AUTO` (változatlan, NEM `MANUAL`) | a state_changed **nem** generál `manual_change_on/off` eseményt (kizárva, lásd B2.2/#3-4); a `device_state` frissül, a `sensor.<name>_device_last_changed` csak az előző ismert logikai értéktől való eltéréskor; a fizikai eltérést (`off` vs. `expected_state`=BE) a következő `state_sync` javítja ki |
| T22 | `MANUAL` (manual_timeout>0); `target_entity_id` `unavailable` volt, most visszatér egy tetszőleges állapottal | *(target_entity_id state_changed: `unavailable` → `on`/`off`)* | `MANUAL` (változatlan) | nincs `manual_change_on/off`, nincs timer-újraindítás, nincs service call — a poller MANUAL alatt amúgy sem nyúlna hozzá (B3.B) |
| T23 | `AUTO`, cron szerinti `timed_state`=KI | külső automatizmus `switch.turn_on` hívása a `switch.<name>_timed_state` entitásra; több perc eltelik cron-találat nélkül | `AUTO` | `timed_state`=BE, `expected_state`=BE; a percenkénti cron-kiértékelés fut, de nem billenti vissza a külső értéket |
| T24 | T23 utáni aktív külső ütemezési parancs | a következő tényleges ON vagy OFF cron-találat | `AUTO` | a külső parancs megszűnik; `timed_state` és `expected_state` a cron értékét veszi fel akkor is, ha az érték azonos volt a külső parancséval |
| T25 | aktív, perzisztált külső ütemezési parancs | HA-újraindítás | a mentett `AUTO`/`MANUAL` állapot | ha a kiesés alatt nem volt újabb cron-találat, a külső érték marad; ha volt, a frissen kiszámolt cronérték nyer |

### Device- és dashboard-kártya elfogadási tesztek

| # | Kiindulás / művelet | Elvárás |
|---|---|---|
| UI1 | Egy Timed Switch config entry betöltődik | Pontosan egy HA Device jön létre `(DOMAIN, entry_id)` azonosítóval, és a B2.3 összes saját entitása ehhez tartozik. |
| UI2 | A felhasználó a kártyaválasztóban kiválasztja a `switch.<name>_expected` entitást | A Timed Switch Card ajánlásként megjelenik, és egyetlen kártyaként hozzáadható. |
| UI3 | A kártya csak az `entity: switch.<name>_expected` konfigurációval betöltődik | Automatikusan megtalálja ugyanazon példány kapcsolóit, number- és sensor-entitásait. |
| UI4 | A kártyán kapcsolót vagy number értéket módosítanak | A megfelelő szabványos HA service call fut; az eredmény azonos az entitás saját More info felületével. |
| UI5 | A Controller entitásállapotot frissít | A kártya újratöltés nélkül mutatja az új állapotokat, időpontokat és hibajelzést. |
| UI6 | Egy másodlagos entitás hiányzik, letiltott vagy `unavailable` | A kártya nem omlik össze; a többi vezérlő működik, a hiányzó érték `—`. |
| UI7 | A dashboard keskeny mobilnézetre vált | A vezérlők vízszintes görgetés nélkül, ugyanazon egy kártyán maradnak használhatók. |
| UI8 | A HA/integráció frissen települ vagy frissül | A kártya resource automatikusan elérhető; nem kell fájlt másolni vagy resource-t kézzel felvenni. |
| UI9 | A felhasználó kód nélkül ad hozzá kártyát | Entitás alapján minden Timed Switch példány `Expected` kapcsolója felajánlja a komplett Timed Switch Cardot; közvetlen kártyaválasztáskor grafikus, az integráció kapcsolóira szűrt entitásválasztó jelenik meg, és az első elérhető példány az alapértelmezett. |
| UI10 | Új Timed Switch létrehozása, Virtual Switch nincs telepítve | A célválasztóban a jelenlegi beépített virtuális cél és a meglévő entitás választása látható; Virtual Switch létrehozási lehetőség nincs. |
| UI11 | Új Timed Switch létrehozása, Virtual Switch telepítve | A célválasztó a `built_in_virtual`, `existing_entity` és `new_virtual_switch` lehetőséget is felajánlja. |
| UI12 | `existing_entity` kiválasztása után egy meglévő `switch.<virtual_name>_main` kerül kiválasztásra | Ez lesz a `target_entity_id`; a Timed Switch külső switchként, a meglévő állapotgép módosítása nélkül vezérli. |
| UI13 | `new_virtual_switch` kiválasztása és a Virtual Switch config flow sikeres befejezése | Létrejön az önálló Virtual Switch entry/Device, és annak `*_main` entitása lesz az új Timed Switch `target_entity_id` értéke. |
| UI14 | A felhasználó megszakítja az új Virtual Switch létrehozását | Nem jön létre félkész Timed Switch; a flow visszatér a célválasztáshoz. |
| UI15 | Egy Virtual Switchhez kapcsolt Timed Switch entryt törölnek | A Virtual Switch entry és Device megmarad. |
| UI16 | A Device oldal megjeleníti az entitásokat | A `Manual Override` a Controls blokkban, a két hátralévőidő-szenzor és a három állapotváltási időbélyeg a Diagnostic blokkban jelenik meg. |
| UI17 | Az Expected, Timed State vagy Device logikai értéke önállóan változik | Csak a hozzá tartozó `Since ... Change` időbélyeg frissül; a célentitás azonos ON/OFF értékű attribútumfrissítése egyik időbélyeget sem módosítja és nem indít manuális módot. Egy vezérlési esemény következményeként ténylegesen megváltozó több kapcsoló időbélyege természetesen ugyanabban az eseménysorban frissülhet. |
| UI18 | Number- vagy cron-entitást egymás után módosítanak | Minden mentés az aktuális config entry options értékeit egészíti ki; egy későbbi módosítás nem írhatja felül vagy törölheti a korábban mentett `manual_timeout`, `sync_interval`, `on_crons` vagy `off_crons` értéket. |

**Negatív tesztek** (illegális/no-op esemény adott állapotban → nem történhet felesleges akció):

| # | Állapot | Esemény | Elvárás |
|---|---|---|---|
| N1 | `AUTO` (device_state already == expected_state) | `state_sync` | változatlan állapot, **nincs** service call (idempotencia) |
| N2 | `MANUAL` | `state_sync` | változatlan állapot, nincs akció — a poller nem nyúl a kapcsolóhoz felülbírálás alatt |
| N3 | `MANUAL` (`switch.<name>_is_manual_mode` már bekapcsolva) | `override_set` (ismételt bekapcsolási kísérlet) | változatlan állapot, nincs akció — HA nem is tüzel state_changed-et azonos értékre, a tábla-cella is no-op (idempotencia) |

### ELERHETOSEGI gép

| # | Kezdőállapot | Eseménysor | Várt végállapot | Várt akciók |
|---|---|---|---|---|
| T13 | `AVAILABLE` | `became_unavailable` | `UNAVAILABLE` | naplózás, diagnosztikai jelzés BE — **a FŐ gép eközben változatlanul, függetlenül tovább működik** |
| T14 | `UNAVAILABLE` | `became_available` | `AVAILABLE` | naplózás, diagnosztikai jelzés KI |

## B6. Nyitott kérdések

> Amit az AI-nak meg kell kérdeznie, mielőtt kódot ír.

- [ ] **Második specifikációs kör témája (nem blokkolja a mostani munkát):** teljes, explicit "amíg vissza nem kapcsolom" BYPASS mód — indoklás és a jelenlegi közelítő megoldás (`manual_timeout=0`): lásd B4/11.
- [ ] `switch.<name>_device` viselkedése `button` domainű `target_entity_id` esetén: mivel a `button` domainnek nincs on/off állapota, nem világos, létrejöjjön-e egyáltalán ez az entitás button célnál, és ha igen, mit jelentsen a kézi átbillentése — lásd B3.4/#6.
- [ ] `target_entity_id` **NEM** élőben (reload nélkül) cserélhető jelenleg — ellentétben a `on_crons`/`off_crons`/`manual_timeout`/`sync_interval` paraméterekkel (B2.4), a `target_entity_id` megváltoztatása az options flow-ban egy teljes integráció-reload-ot igényel, hogy a Controller újra feliratkozzon az új entitásra. Ez tudatos, jelenleg el nem döntött kérdés: kell-e ide is élő váltás, vagy ez a paraméter marad kivétel.
