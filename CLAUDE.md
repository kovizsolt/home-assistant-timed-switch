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
├── CLAUDE.md            # ez a fájl — tartós szabályok
├── SPEC.md              # módszertan + specifikáció (igazság forrása)
├── src/
│   ├── state_machine.py # generikus motor
│   └── transition_table.py  # az átmeneti tábla adatként
└── tests/
    └── test_transitions.py
```
