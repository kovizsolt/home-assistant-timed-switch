# Projekt: Home Assistant állapotgép (Python)

Ez a fájl a projekt tartós szabályait tartalmazza. Minden munkamenet elején olvasd el, és tartsd be a teljes beszélgetés alatt.

**A részletes módszertan és a specifikáció: `SPEC.md`.**

---

## 0. Nyelv

Magyarul kommunikálj.

A kódban a változó-, entitás- és állapotnevek, valamint a kommentek **angolul**, snake_case formában íródnak — igazodva a korábbi `timed_switch` projekt (`/MyDevelopment/Ansible/MyInventory.home/roles/home-assistant/custom_components/timed_switch/`) szóhasználatához, hogy a két projekt könnyen összevethető maradjon, és mert a végleges komponens publikálása is angol nyelven történik.

Ez a szabály a `SPEC.md` B2 szótárára is vonatkozik: az állapot-, esemény-, entitás- és paraméterneveket angolul rögzítjük (lásd `SPEC.md` B rész bevezetője). A specifikáció prózája (magyarázatok, indoklások) továbbra is magyar marad.

## 1. Kódírás előtt — KÖTELEZŐ

Mielőtt bármilyen kódot írnál, **külön szakaszban sorold fel**:

1. **Feltételezések** — amit a specifikáció nem mond ki, de a kódhoz feltételeznem kellett.
2. **Hiányzó információk** — amit meg kell kérdeznem, mielőtt folytatom.
3. **Ellentmondások** — ha a specifikáció két pontja ütközik.

Ha ez a lista nem üres, **állj meg és kérdezz.** Ne találgass, ne tölts ki hézagot magadtól. A megakadás olcsóbb, mint a rossz feltételezés.

## 2. Sorrend: tesztek → jóváhagyás → kód

Kövesd a `SPEC.md` A2/4 munkarendjét szó szerint: `SPEC.md` B3 tábla → B5 elfogadási tesztek → **emberi jóváhagyás** → csak ezután implementáció. Ott van az is leírva, mi a teendő, ha egy teszt utólag rossznak bizonyul.

## 3. Implementációs szabályok

- Táblavezérelt motor — az elvet lásd `SPEC.md` A2/5: az átmeneti tábla **adatszerkezet** (dict / lista), nem szétszórt `if/elif` lánc, és a kód tábla-sorai a `SPEC.md` B3 szakaszával egymás mellé tehetők.
- Az állapot tárolása `input_select` helperben történik (lásd `SPEC.md` A4), hacsak a specifikáció mást nem mond.
- Minden akció legyen idempotens, hacsak a specifikáció kifejezetten mást nem ír elő.
- Minden állapotátmenet naplózva legyen: `honnan → hova`, kiváltó esemény, időbélyeg.
- Ismeretlen (állapot, esemény) pár esetén: naplózz figyelmeztetést, de **ne dobj kivételt** és ne változtass állapotot.
- Ne legyen csendes `except: pass`. Minden elnyelt hiba naplózandó.

## 4. Szótárfegyelem

Az elvet lásd `SPEC.md` A2/2. Gyakorlatban: a `SPEC.md` B2 szakaszában rögzített neveket használd **szó szerint** — szinoníma, fordítás, rövidítés nélkül.

Ha új állapotra vagy eseményre van szükség, előbb **kérd a `SPEC.md` B2 bővítését**, csak utána használd.

## 5. Dokumentáció, nem emlékezet

A Home Assistant, Pyscript és AppDaemon API-k gyakran változnak, és a betanítási adataid elavultak lehetnek.

**Ellenőrizd dokumentációból** (ne emlékezetből):
- Pyscript dekorátorok pontos neve és paraméterei (`@state_trigger`, `@time_trigger`, `@service`)
- `service.call` / `hass.services` szintaxis
- `input_select` és `timer` szolgáltatásnevek
- AppDaemon `self.listen_state` / `self.run_in` szignatúrák

Ha nem tudod ellenőrizni, **jelezd expliciten**, hogy az adott rész verifikálatlan.

## 6. Változtatások köre

- Csak azt módosítsd, amit kértek. Ne írj át működő kódrészt "közben, ha már ott jártál" alapon.
- Ne generálj mellékfájlokat (README, példák, segédszkriptek) kérés nélkül.
- Ha a `SPEC.md` és a kód eltér, a `SPEC.md` az igazság forrása — jelezd az eltérést, ne a kódhoz igazítsd a specifikációt.

## 7. Hibajelentés formátuma

Ha hibát jelentek, ilyen formában fogom:

```
Állapot volt:  ...
Esemény jött:  ...
Ami történt:   ...
Amit vártam:   ...
```

Válaszban először **azonosítsd az érintett táblacellát** a `SPEC.md` B3 szakaszában, és mondd meg, a specifikáció vagy az implementáció hibás-e. Csak ezután javíts.

## 8. Projektstruktúra

```
.
├── CLAUDE.md                         # ez a fájl — tartós szabályok
├── SPEC.md                           # módszertan + specifikáció (igazság forrása)
├── VERSION                           # build-verzió, ld. 9. pont
├── deploy.sh                         # deploy a docker dev/teszt HA-ba, ld. 10. pont
├── custom_components/timed_switch/   # a tényleges HA custom integráció (ez deployol)
│   ├── manifest.json
│   ├── const.py
│   ├── state_machine.py              # generikus, tábla-vezérelt motor (SPEC.md A2/5)
│   ├── transition_table.py           # SPEC.md B3.A/B3.B mint adat
│   ├── controller.py                 # Controller: mindkét gép, I/O, timerek, Store
│   ├── helpers.py                    # cron-kiértékelés, PersistedState
│   ├── config_flow.py
│   ├── switch.py / sensor.py / number.py / binary_sensor.py
│   ├── __init__.py
│   ├── strings.json
│   └── translations/
└── tests/
    └── test_transitions.py           # a state_machine.py + transition_table.py tesztje,
                                       # HA-futásidő nélkül (ld. 10. pont)
```

Megjegyzés: a `state_machine.py`/`transition_table.py` a `custom_components/timed_switch/`
alatt élnek (nem külön `src/`-ben), mert HA custom integrációként ezeknek fizikailag a
komponens-mappában kell lenniük ahhoz, hogy deployolhatók legyenek — az A2/5 elv (tábla mint
adat, generikus motor) ettől függetlenül érvényes, csak a fájlok helye tér el az eredeti
tervtől.

## 9. Verziószám

Minden érdemi kódmódosításnál emelni kell a build-számot: a `VERSION` fájl utolsó (4
számjegyű) szegmensét, és a `custom_components/timed_switch/manifest.json` `version`
mezőjét ugyanarra az értékre — pl. `0.1.0000` → `0.1.0001`. A `deploy.sh` ezt automatikusan
elvégzi minden futtatáskor, kézzel nem kell piszkálni.

## 10. Fejlesztői/deploy környezet

- **Cél:** élő docker dev/teszt Home Assistant, host-perzisztencia: `/mnt/3-Data/docker.data/home-assistant` (konténerben `/config`), konténer neve: `homeassistant`.
- **Domain-döntés:** a komponens szándékosan a `timed_switch` domain-t/mappát használja, és ezzel **felülírja** a korábbi (Ansible-es, `/MyDevelopment/Ansible/MyInventory.home/roles/home-assistant/custom_components/timed_switch/`) projekt kódját, ami korábban ugyanezen a domain-en, "MyTimer" config entry néven futott ebben a HA-ban. Ez tudatos, jóváhagyott döntés (nem véletlen ütközés) — az új komponens felváltja a régit, nem mellette fut.
- **Deploy:** `./deploy.sh` a projekt gyökeréből. Nem `rsync`/`sudo` a host-útvonalra (a `/mnt/3-Data/docker.data/home-assistant` root-tulajdonú, a fejlesztő user nincs a `root` csoportban, és a sudo jelszót igényel, nem automatizálható) — hanem a docker daemonon keresztül, `docker exec`/`docker cp`-vel, ami a konténerben **root**-ként fut, így a hívó user `docker` csoporttagsága elég, sudo nélkül. A script emeli a verziót, majd (opcionálisan, `--no-restart`-tal kihagyható) újraindítja a konténert és kiírja a friss logot.
- **Éles teszt, nem csak elmélet:** a SPEC.md-et és a kódot ebben a környezetben, valós HA-újraindításokkal, log-alapján validáljuk — ha egy teszt vagy feltételezés téves, itt derül ki, nem a felhasználó éles rendszerén.

## 11. Verifikált HA-API megjegyzések (HA 2025.9.4, ellenőrizve élőben)

A CLAUDE.md 5. pontja szerint ("Dokumentáció, nem emlékezet") ezek a tények **ténylegesen
ellenőrizve** lettek ebben a HA-verzióban (nem feltételezés), hogy legközelebb ne kelljen
újra kitalálni/hibázni:

- `homeassistant.helpers.dispatcher.async_dispatcher_send` **szinkron** `@callback` függvény
  ebben a verzióban, NEM awaitolható coroutine — `await`-elve `TypeError: object NoneType
  can't be used in 'await' expression` hibát dob. Simán hívandó, await nélkül.
- `async_dispatcher_connect` szintén szinkron, egy unsubscribe callable-t ad vissza
  közvetlenül (nem awaitolandó).
- **Device-csoportosítás kötelező minden entitáshoz** (`device_info` property, azonos
  `(DOMAIN, entry_id)` identifiers minden entitáson) — enélkül az entitások nem jelennek meg
  egy közös eszközkártyaként a *Beállítások → Eszközök és szolgáltatások* nézetben, csak
  szórt, kontextus nélküli listaelemekként. Lásd SPEC.md B2.3.
  **Fontos csapda:** ha egy entitás `unique_id`-ja már regisztrálva volt a device_info
  hozzáadása ELŐTT (pl. korábbi kód-verzióból maradt entity registry bejegyzés), a
  `device_id` utólag NEM töltődik ki automatikusan újraindításra — az entity registry
  releváns sorait törölni kell (`.storage/core.entity_registry`), hogy a következő indulás
  frissen, a device-linkeléssel együtt regisztrálja őket.
- `async_call_later(hass, delay_seconds, callback)` és `async_track_time_interval(hass,
  callback, timedelta)` — mindkettő szinkron, egy cancel-callable-t ad vissza.
- `docker exec <container> whoami` → `root` ebben a HA docker image-ben — a konténerben
  minden fájlművelet root jogosultsággal fut, függetlenül a host-usertől.
