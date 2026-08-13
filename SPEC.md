# Állapotgép specifikáció — Home Assistant / Python

> Ez a dokumentum két részből áll: **A rész** — a munkamódszer (ezt ne töröld, ez a projekt "alkotmánya"). **B rész** — a kitöltendő specifikációs sablon.
>  A cél: olyan specifikáció, amiben nincs értelmezési rés, ezért a kód nem *értelmezése*, hanem *átirata* a specifikációnak.
>  **Nyelvi megjegyzés:** a próza–szótár nyelvi megosztás szabálya kanonikusan a `CLAUDE.md` 0. pontjában van rögzítve. Az alábbi B2 szótár emiatt szándékosan tér el az A2/2 pont illusztrációjától, ami egy általános, projekt-független példát mutat be.

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

Az ütemterv-kiértékelés folyamatosan, a manuális felülbírálástól függetlenül fut, és mindig frissíti a belső "timed_state" (BE/KI) tulajdonságot — ez a cron nyers, aktuális kimenete, AUTO és MANUAL alatt egyaránt frissül. A belső "expected_state" ebből származik: **AUTO** módban élőben követi a "timed_state"-et; **MANUAL** módban a kézi beavatkozás értékén fagyva marad, a "timed_state" háttérbeli változásaira nem reagál azonnal — csak a MANUAL-ból való visszatéréskor veszi át a pillanatnyi "timed_state" értéket. Azt szabályozzuk, hogy az "expected_state" ténylegesen eljusson-e a fizikai kapcsolóhoz.

Egy külön, periodikus állapot-ellenőrzés (poller, `state_check` esemény) szinkronban tartja a virtuális célt és a fizikai kapcsoló állapotát, amikor nincs aktív felülbírálás — ez a failsafe mechanizmus elveszett service call, HA- vagy hálózati kiesés esetére.

Manuális beavatkozás esetén a kapcsoló egy konfigurált időtartamig ("manual_timeout") a manuális vezérlés szerint marad, utána automatikusan visszaáll, és az ekkor éppen aktuális ütemterv-célt követi. A `manual_timeout=0` speciális érték kivétel: ekkor nincs lejárati timer, a manuális állapot a következő ütemezett váltásig tart (lásd B2.4, B3.A).
```

**Futtatókörnyezet:** ☒ Custom integration ☐ Pyscript ☐ AppDaemon

## B2. Szótár

> Ez a gép **két független állapotgépből** áll (SPEC.md A4 elve szerint: "ha egymástól független dolgok futnak párhuzamosan → két külön állapotgép"):
> - **FŐ gép** — mi vezérli a kapcsolót: az ütemterv, vagy egy aktív manuális felülbírálás. (angolul: *main state machine*)
> - **ELERHETOSEGI gép** — a vezérelt entitás elérhető-e; tisztán diagnosztikai, NEM hat a FŐ gép működésére (failsafe elv). (angolul: *availability state machine*)

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
| 1 | `schedule_on` | ütemterv (`on_crons` cron trigger) VAGY a `switch.<name>_timed_state` UI-kapcsoló kézi BE-re állítása (teszt célra — a valódi cronra várakozás nélkül szimulálja ugyanazt). Mindkét forrás egyenértékű: mindig a `timed_state`-et frissíti; a hatása AUTO/MANUAL módban eltérő — lásd B3.A. |
| 2 | `schedule_off` | ugyanez KI irányban |
| 3 | `manual_change_on` | a kapcsolt eszközt tükröző entitások bármelyikének (`target_entity_id`, `switch.<name>_expected` VAGY `switch.<name>_device`) állapota BE-re változott, amit NEM a komponens saját service call-ja/írása és NEM az időzítő/ütemterv okozott (fizikai kapcsoló, HA-UI a `target_entity_id`-n, a `switch.<name>_expected` UI-kapcsoló, vagy a `switch.<name>_device` UI-kapcsoló — mind a négy egyenértékű bemenet). A `target_entity_id`-re vonatkozó megkülönböztetés mechanizmusa: lásd B3.3; a `switch.<name>_expected` és `switch.<name>_device` saját, komponens-implementálta entitások, itt nincs szükség ugyanerre a védelemre a saját kezelőjükön (lásd B2.3, B3.3). Bármelyik forrásból is jön, az esemény hatására `expected_state` a kiváltó iránynak megfelelő értékre áll (lásd B3.A). **Kizárás:** ha a `target_entity_id` state_changed eseményének RÉGI állapota `unavailable`/`unknown` volt (azaz az esemény egyben `became_available`-t is kivált — lásd B2.2b/#2, B3.B) — ez sosem minősül `manual_change_on/off`-nak, csak a device_state / `sensor.<name>_device_last_changed` frissül belőle; a szinkronizálást a soron következő `state_check` végzi el (AUTO módban). |
| 4 | `manual_change_off` | ugyanez KI irányban |
| 5 | `manual_timeout_expired` | belső timer, `manual_timeout` config paraméter szerint — csak akkor fordulhat elő, ha `manual_timeout > 0` (0 esetén nincs timer, lásd B2.4) |
| 6 | `override_cleared` | explicit felhasználói akció a felülbírálás azonnali megszüntetésére — szolgáltatásból, gombról, vagy a `switch.<name>_is_manual_mode` UI-kapcsoló kézi kikapcsolásából |
| 7 | `state_check` | periodikus poller trigger, `check_interval` config paraméter szerint — csak akkor fordulhat elő, ha `check_interval > 0` (0 esetén a poller teljesen le van tiltva, lásd B2.4) |
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
| bemenet + kimenet (UI) | `switch.<name>_expected` | switch | Az `expected_state`-et mutatja és kézzel is állítja. AUTO módban élőben követi a `switch.<name>_timed_state`-et; MANUAL módban a kézi beavatkozás értékén fagyva marad (lásd B1, B3.A). Kézi kapcsolása `manual_change_on`/`manual_change_off` (lásd B2.2/#3-4). Saját, komponens-implementálta entitás — nincs önhivatkozási kockázat (lásd B3.3). Attribútum: `device_available` — a `target_entity_id` ELERHETOSEGI állapotát jelzi (lásd B2.1b); ettől függetlenül a kapcsoló vezérelhetősége változatlan marad (a beépített HA `unavailable` szürkítés itt szándékosan NEM használt, mert az letiltaná a vezérlést — lásd `binary_sensor.<name>_problem` is). |
| bemenet + kimenet (UI) | `switch.<name>_timed_state` | switch | A cron ütemterv NYERS, folyamatosan frissülő kimenete — AUTO-ban és MANUAL-ban egyaránt frissül, függetlenül a felülbírálástól. Kézi átbillentése valódi `schedule_on`/`schedule_off` eseményt vált ki (teszt célra, a tényleges cron-időpont megvárása nélkül — lásd B2.2/#1-2). Saját, komponens-implementálta entitás, nincs önhivatkozási kockázat. Attribútum: `next_schedule` (a következő cron-váltás abszolút időpontja). |
| bemenet + kimenet (UI) | `switch.<name>_is_manual_mode` | switch | A FŐ gép állapotát mutatja és kézzel is váltja: `is_on=True` ⇒ manuális mód (`MANUAL`), `is_on=False` ⇒ időzített mód (`AUTO`). Kézi bekapcsolása `override_set`, kikapcsolása `override_cleared` (lásd B2.2/#6, #8). Saját, komponens-implementálta entitás — nincs szüksége context-echo védelemre. |
| bemenet + kimenet (UI) | `switch.<name>_device` | switch | A `target_entity_id` kétirányú tükre: bármelyik irányból (itt vagy közvetlenül a `target_entity_id`-n) történő váltás egyenértékű. Kézi (nem a komponens saját service call-ja miatti) váltása `manual_change_on`/`manual_change_off` eseményt vált ki, ugyanúgy mintha közvetlenül a `target_entity_id`-t kapcsolták volna át (lásd B2.2/#3-4, B3.3 kiterjesztett hatóköre). Elérhetőség: a `target_entity_id` ELERHETOSEGI állapotát tükrözi. |
| kimenet (UI) | `binary_sensor.<name>_problem` | binary_sensor (`device_class: problem`) | ON, ha az ELERHETOSEGI gép `UNAVAILABLE` állapotban van (B2.1b) — feltűnő, alapértelmezett HA-jelzés (a legtöbb beépített kártyán/area-nézeten konfiguráció nélkül is látszik), kiegészítve a `switch.<name>_expected` `device_available` attribútumát. |
| kimenet (UI) | `sensor.<name>_manual_remaining` | sensor (`óó:pp:ss`, élő, folyamatosan frissülő állapot) | MANUAL módban a `manual_timeout` hátralévő ideje; `manual_timeout=0` esetén nincs értelmezve / `—`. |
| kimenet (UI) | `sensor.<name>_since_last_change` | sensor (`device_class: timestamp`) | Az `expected_state` utolsó váltásának ABSZOLÚT időpontja. Csak ez van tárolva — a "mennyi ideje" relatív megjelenítés a HA frontend natív timestamp-renderelése, nincs külön számolva/tárolva. |
| kimenet (UI) | `sensor.<name>_device_last_changed` | sensor (`device_class: timestamp`) | A `target_entity_id` utolsó ténylegesen észlelt állapotváltásának abszolút időpontja. |
| kimenet (UI) | `number.<name>_manual_timeout` | number (mp) | Futásidejű, config-alapértéktől eltérő `manual_timeout` beállítása. |
| kimenet (UI) | `number.<name>_check_interval` | number (mp) | Futásidejű, config-alapértéktől eltérő `check_interval` beállítása; `0` = a poller (`state_check`) teljesen kikapcsolva (lásd B2.4). |

**Device-csoportosítás:** a fenti táblázat összes entitása (a `target_entity_id` kivételével, ami külső entitás) egyetlen közös HA Device alá tartozik, komponens-példányonként egy Device (azonosító: `(DOMAIN, entry_id)`). Enélkül az entitások a HA UI-n szórt, kontextus nélküli listaelemekként jelennek meg, nem egy áttekinthető eszközkártyaként — ez a felhasználói felület szempontjából ugyanolyan kötelező elem, mint bármelyik fenti sor.

### B2.4 Időzítők / paraméterek

| Név | Érték | Jelentés |
|---|---|---|
| `on_crons` / `off_crons` | felhasználó adja meg — cron-szerű kifejezések listája, soronként vagy vesszővel elválasztva, `#` a komment, `croniter` szintaxis, perc-pontosság | Külön ON és OFF cron-lista (nem egy kombinált tábla). **Élőben (reload nélkül) szerkeszthető** az options flow-n keresztül — a módosítás azonnal, integráció-újraindítás nélkül érvénybe lép és újraszámolja a `timed_state`-et/`next_schedule`-t. Ha mindkét lista üres: nincs időzítés — `timed_state` sosem változik (a `default_state` értéken marad), `next_schedule` értelmezhetetlen (`—`). |
| `manual_timeout` | felhasználó adja meg (mp), alapértelmezett **600** | Mennyi ideig érvényes egy manuális felülbírálás, mielőtt automatikusan visszaáll az ütemtervre. **Speciális eset: `manual_timeout=0`** → nincs lejárati timer; a `MANUAL` állapot a következő `schedule_on`/`schedule_off` eseményig tart (lásd B3.A). Futásidőben felülbírálható a `number.<name>_manual_timeout` entitással, függetlenül a config alapértéktől. |
| `check_interval` | felhasználó adja meg (mp), alapértelmezett **60** | A poller (`state_check`) periódusideje. **Speciális eset: `check_interval=0`** → a poller teljesen kikapcsolva, `state_check` esemény soha nem generálódik, amíg vissza nem áll `>0` értékre. Futásidőben felülbírálható a `number.<name>_check_interval` entitással. |
| `default_state` | felhasználó adja meg (BE/KI) | A kapcsoló kezdő értéke, ha nincs érvényes mentett állapot és/vagy még nincs kiértékelhető ütemterv. |
| `notify_events` | felhasználó adja meg (bool), alapértelmezett **false** | Ha igaz, HA `persistent_notification` jön létre ütemezett célváltáskor és enforce-akciónál — lásd B4/10. |

## B3. Átmeneti tábla

> **MINDEN cella kötelező.** Ahol nincs teendő, írd: `— (ignore)`. Formátum egy cellában: `CÉLÁLLAPOT [guard] → akció`

### B3.A — FŐ gép

| Állapot \ Esemény | `schedule_on` | `schedule_off` | `manual_change_on` | `manual_change_off` | `manual_timeout_expired` | `override_cleared` | `override_set` | `state_check` |
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
1. Store-ból betöltjük a mentett Controller-állapotot: state (AUTO/MANUAL), expected_state (csak MANUAL esetén releváns, a fagyasztott kézi érték), manual_until lejáratának ABSZOLÚT időpontja (None, ha manual_timeout==0 mellett lépett MANUAL-ba).
2. Ha nincs mentett adat vagy érvénytelen: state = AUTO, expected_state = default_state.
3. `timed_state`-et (és a `next_schedule` attribútumot) MINDIG frissen, a cron-kifejezésekből és a jelenlegi időpontból számoljuk újra — ez sosem perzisztált érték, tiszta függvénye az `on_crons`/`off_crons`-nak és az aktuális időnek (a HA-kiesés alatt eltelt idő "mintha meg sem történt volna" — nem vész el információ, mert a cron-kifejezések maguk perzisztensek).
4. Ha a mentett állapot **AUTO** volt: `expected_state` := a frissen számolt `timed_state`; a B3.1 AUTO entry akció elvégzi a kapcsoló szinkronizálását.
5. Ha a mentett állapot **MANUAL** volt, és a mentett lejárati időpont már elmúlt a kiesés alatt (csak manual_timeout > 0 esetén értelmezhető): → AUTO-ra lépünk; `expected_state` := a frissen számolt `timed_state`; a B3.1 entry akció elvégzi a kapcsoló beállítását.
6. Ha a mentett állapot MANUAL volt, manual_timeout == 0 (nincs lejárati időpont): → MANUAL marad; `expected_state` a mentett (fagyasztott) értéken marad; a visszatérés továbbra is a következő schedule_on/schedule_off eseménytől függ.
7. Egyébként (MANUAL és a lejárat még nem múlt el): → MANUAL marad, `expected_state` a mentett (fagyasztott) értéken marad, a timer a mentett abszolút lejárati időponttal folytatódik.
8. Az ELERHETOSEGI gép mindig `UNAVAILABLE`-lel indul (nem perzisztált, lásd B2.1b), és az első valós `target_entity_id` állapot-lekérdezéskor azonnal átvált `AVAILABLE`-re, ha az elérhető.
```

### B3.3 Önhivatkozás elleni védelem (echo-suppression)

```
Amikor a komponens saját maga hív service call-t a target_entity_id domainjének megfelelő szolgáltatással (switch/input_boolean/light/script domainnél turn_on/turn_off, button domainnél press — ld. B3.4) a target_entity_id-re — az AUTO állapot entry/state_check korrekciója, a MANUAL→AUTO átmenet szinkronizációja, vagy a switch.<name>_expected-ről / switch.<name>_device-ról érkező manual_change_on/off esemény kapcsán a target_entity_id-re történő irány-szinkronizáció során — az ebből eredő state_changed esemény NEM minősül manual_change_on/off eseménynek. Button célnál ez a mechanizmus nem releváns, mivel arra a domainre nincs state_changed-alapú megfigyelés (ld. B3.4).

Mechanizmus: a service call meghívásakor visszakapott HA `Context` objektum `id`-ját eltároljuk (`_last_own_context_id`). A target_entity_id state_changed eseményének feldolgozásakor a `new_state.context.id`-t ezzel összevetjük:
  - ha egyezik → a változást a komponens okozta, az eseményt eldobjuk (nem generálunk belőle manual_change_* eseményt, de a device_state és a `sensor.<name>_device_last_changed` frissül);
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
   - a `state_check` (poller) button célnál mindig no-op — nincs mit ellenőrizni/enforce-olni;
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
| 8 | Idempotens-e minden akció? (kétszer jövő esemény → egyszer fut?) | Igen — a CLAUDE.md 3. szabálya kötelezővé teszi. Pl. a `state_check` és a `schedule_on/off` cellák is guardolva vannak (`device_state != expected_state`), hogy felesleges service call ne fusson kétszer. |
| 9 | Van olyan átmenet, amit ember kézzel is kiválthat a UI-ról? | Igen, mindkét irányban. MANUAL-ba lépés kézzel: a `target_entity_id`, a `switch.<name>_expected` vagy a `switch.<name>_device` átkapcsolásával (`manual_change_on/off`), vagy a `switch.<name>_is_manual_mode` bekapcsolásával (`override_set`). AUTO-ra visszaállás: automatikusan (`manual_timeout_expired`) VAGY explicit manuálisan (`override_cleared` — szolgáltatásból, gombról, vagy a `switch.<name>_is_manual_mode` kikapcsolásával). Emellett a `switch.<name>_timed_state` kézi átbillentése is UI-ból kiváltható, valódi `schedule_on/off` eseményként (teszt célra — lásd B2.2/#1-2). |
| 10 | Naplózás: melyik átmeneteket kell logolni / értesítést küldeni? | Minden állapotátmenet naplózva (CLAUDE.md 3. szabálya szerint kötelező: honnan → hova, kiváltó esemény, időbélyeg). HA-értesítés (`persistent_notification`): opcionális, a `notify_events` config paraméter kapcsolja be/ki, ütemezett célváltáskor és enforce-akciónál küld (lásd B2.4). |
| 11 | Van "vészleállító" / bypass állapot? | Nincs külön, explicit BYPASS állapot ebben a körben. Helyette a `manual_timeout=0` paraméterérték a meglévő `MANUAL` állapotban engedi, hogy a felülbírálás időzítő nélkül maradjon aktív, és csak a következő `schedule_on`/`schedule_off` esemény zárja le (lásd B2.4, B3.A). Egy teljes, explicit "amíg vissza nem kapcsolom" BYPASS mód (saját állapottal, saját szolgáltatással, a schedule-tól is függetlenül) továbbra sem témája ennek a körnek — lásd B6. |
| 12 | Mi legyen, ha egy akció (service call) hibára fut? | Naplózás + hibajelzés, nincs külön retry-állapotgép/logika. A normál működés (a soron következő `state_check` vagy `schedule_on/off` esemény) magától újra megpróbálja — ez a "failsafe" elv, amit a poller biztosít. |
| 13 | Hogyan különböztetjük meg a komponens saját service call-ja okozta állapotváltást a valódi manuális beavatkozástól? | HA `Context.id` összevetés a service call és a state_changed esemény között. Részletes mechanizmus: B3.3. |
| 14 | Mi történik `button` domainű cél entitásnál, aminek nincs `on`/`off` állapota? | Minden `expected_state`-váltás (mindkét irányban) egyetlen `button.press` hívást jelent, `device_state` összevetés nélkül; a `state_check` poller button célnál no-op; fizikai/UI gombnyomás sosem generál `manual_change_on/off` eseményt (nincs megfigyelhető állapot). Részletes szabály: B3.4. |
| 15 | Mi történik, ha a `target_entity_id` `unavailable`/`unknown`-ból visszatér egy konkrét `on`/`off` állapottal (pl. áramkimaradás után megjegyzett állapot)? | Ez NEM minősül manuális beavatkozásnak — a `became_available`-lel egybeeső state_changed kizárva a `manual_change_on/off` eseményből (lásd B2.2/#3-4, B3.B). Nincs azonnali kényszerített akció; AUTO módban a soron következő `state_check` szinkronizálja a fizikai kapcsolót az `expected_state`-tel. **Következmény:** ha `check_interval=0` (poller kikapcsolva), egy visszakapcsolódáskori eltérés javítatlan marad, amíg a `check_interval` vissza nem áll `>0`-ra. |

## B5. Elfogadási tesztek

> Ezeket az AI generálja a B3 táblából, **de te hagyod jóvá kód előtt.** Formátum: kezdőállapot → eseménysor → várt végállapot + várt akciók.

### FŐ gép

| # | Kezdőállapot | Eseménysor | Várt végállapot | Várt akciók |
|---|---|---|---|---|
| T1 | `AUTO` (device_state=KI, expected_state=KI) | `schedule_on` | `AUTO` | `expected_state`=BE; kapcsoló BE (service call) |
| T2 | `AUTO` (device_state=BE, expected_state=BE) | `manual_change_off` | `MANUAL` | `manual_timeout>0`: timer indul (`manual_timeout`); nincs extra service call |
| T3 | `MANUAL` (expected_state=KI, manual_timeout>0) | `manual_timeout_expired` | `AUTO` | kapcsoló beállítása `expected_state` (KI) szerint |
| T4 | `MANUAL` (device_state=KI, felülírás miatt) | `schedule_on` | `MANUAL` (változatlan) | `timed_state`=BE frissül a háttérben; `expected_state` és a fizikai kapcsoló **változatlan** (KI) |
| T5 | `AUTO` (device_state=KI, expected_state=BE — pl. korábban elveszett service call miatt eltért) | `state_check` | `AUTO` (változatlan) | kapcsoló BE (korrekciós service call) |
| T6 | `MANUAL` (expected_state=BE) | `override_cleared` | `AUTO` | kapcsoló beállítása `expected_state` (BE) szerint |
| T7 | Induláskor: mentett `MANUAL`, mentett lejárati időpont **már elmúlt** a HA-kiesés alatt (manual_timeout>0) | *(betöltés / újraindítás)* | `AUTO` | kapcsoló beállítása `expected_state` szerint |
| T8 | `MANUAL` (manual_timeout=0, expected_state=KI) | `manual_change_on` (ismételt kézi kapcsolgatás) | `MANUAL` (változatlan) | `expected_state`=BE (a kézi irány szerint frissül); nincs timer-esemény soha; a `MANUAL`-ból való kilépés csak `schedule_on`/`schedule_off`-ra (azaz `timed_state`-mozgásra) vár |
| T9 | `MANUAL` (manual_timeout=0, expected_state=KI) | `schedule_on` | `AUTO` | `timed_state`=BE; belépéskor `expected_state`=BE (a pillanatnyi `timed_state`-ből); kapcsoló BE — a 0-timeout override így zárul le |
| T10 | `AUTO` (device_state=KI, expected_state=KI) | `state_check` → (a poller saját service call-ja BE-re állítja a device_state-et, ugyanazzal a HA Context-tel) | `AUTO` (nem `MANUAL`!) | a saját service call miatti state_changed esemény **nem** generál `manual_change_on` eseményt (lásd B3.3) |
| T11 | `AUTO` (device_state=KI, expected_state=KI) | `override_set` (forrás: `switch.<name>_is_manual_mode` kézi bekapcsolása) | `MANUAL` | timer indul (`manual_timeout`); `expected_state` változatlan (KI); **nincs** service call (a fizikai eszköz már ott áll, ahol `expected_state`) |
| T12 | `AUTO` (device_state=KI, expected_state=KI) | `manual_change_on` (forrás: `switch.<name>_expected` kézi bekapcsolása) | `MANUAL` | `expected_state`=BE; timer indul (`manual_timeout`); kapcsoló BE (service call a `target_entity_id`-re, hogy kövesse az új célt) — a keletkező state_changed a B3.3 kiterjesztett hatóköre miatt (saját context) **nem** generál újabb `manual_change_on` eseményt |
| T17 | `AUTO` (device_state=KI, expected_state=KI, timed_state=KI) | `switch.<name>_timed_state` kézi átbillentése BE-re | `AUTO` (változatlan) | ugyanaz, mint T1: `timed_state`=BE (valódi `schedule_on` eseményt vált ki); `expected_state`=BE; kapcsoló BE |
| T18 | `MANUAL` (device_state=KI, expected_state=KI, manual_timeout>0) | `switch.<name>_timed_state` kézi átbillentése BE-re | `MANUAL` (változatlan) | ugyanaz, mint T4: `timed_state`=BE a háttérben; `expected_state` és a fizikai kapcsoló **változatlan** |
| T19 | `AUTO` (device_state=KI, expected_state=KI) | `manual_change_on` (forrás: `switch.<name>_device` kézi bekapcsolása) | `MANUAL` | `expected_state`=BE; timer indul (`manual_timeout`); kapcsoló BE (a `switch.<name>_device` handlere továbbítja a service call-t a `target_entity_id`-re) — a keletkező state_changed a B3.3 kiterjesztett hatóköre miatt **nem** generál újabb `manual_change_on` eseményt |
| T20 | `AUTO`, `check_interval=0` | *(idő telik, nincs esemény)* | `AUTO` (változatlan) | `state_check` esemény **soha nem** generálódik, amíg `check_interval` vissza nem áll `>0`-ra — a poller ki van kapcsolva |
| T21 | `AUTO` (expected_state=BE); `target_entity_id` `unavailable` volt, most visszatér `off` állapottal | *(target_entity_id state_changed: `unavailable` → `off`)* | `AUTO` (változatlan, NEM `MANUAL`) | a state_changed **nem** generál `manual_change_on/off` eseményt (kizárva, lásd B2.2/#3-4); csak device_state / `sensor.<name>_device_last_changed` frissül; a fizikai eltérést (`off` vs. `expected_state`=BE) a következő `state_check` javítja ki |
| T22 | `MANUAL` (manual_timeout>0); `target_entity_id` `unavailable` volt, most visszatér egy tetszőleges állapottal | *(target_entity_id state_changed: `unavailable` → `on`/`off`)* | `MANUAL` (változatlan) | nincs `manual_change_on/off`, nincs timer-újraindítás, nincs service call — a poller MANUAL alatt amúgy sem nyúlna hozzá (B3.B) |

**Negatív tesztek** (illegális/no-op esemény adott állapotban → nem történhet felesleges akció):

| # | Állapot | Esemény | Elvárás |
|---|---|---|---|
| N1 | `AUTO` (device_state already == expected_state) | `state_check` | változatlan állapot, **nincs** service call (idempotencia) |
| N2 | `MANUAL` | `state_check` | változatlan állapot, nincs akció — a poller nem nyúl a kapcsolóhoz felülbírálás alatt |
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
