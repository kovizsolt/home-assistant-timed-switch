# Timed Switch

[English documentation](README.md) · [Változásnapló](CHANGELOG.md)

A Timed Switch egy Home Assistant custom integráció kapcsolható eszközök megbízható,
időzített vezérlésére. Használható például egy fizikai okoskapcsoló (Smart Switch),
relé vagy világítás előre megadott időpontokban történő be- és kikapcsolására. Egy
integrációpéldány mindig egy célentitást kezel.

Főbb lehetőségei:

- cron alapú, rugalmas BE/KI ütemezés;
- kézi kapcsolási mód időkorlátos felülbírálással;
- beállítható időközönként folyamatosan ellenőrzi a vezérelt kapcsoló tényleges
  állapotát, és eltérés esetén visszaállítja a kívánt állapotot;
- a működési állapot megőrzésével hibatűrő vezérlést biztosít Home Assistant-
  újraindítás, üzemszünet vagy átmeneti hálózati probléma után is;
- a célentitás elérhetőségének külön diagnosztikai jelzése.

Támogatott célentitások: `switch`, `input_boolean`, `light`, `script` és `button`.

## Követelmények

- Home Assistant 2026.8.2 vagy újabb;
- hozzáférés a Home Assistant `config` könyvtárához;
- újraindítási jogosultság;
- a Lovelace felület használatához a `frontend` és `lovelace` integráció.

A Python-függőséget (`croniter`) a Home Assistant a `manifest.json` alapján
automatikusan telepíti.

## Telepítés

### HACS (ajánlott)

1. Nyisd meg a HACS felületét, majd a jobb felső menüben válaszd a
   **Custom repositories** lehetőséget.
2. Add hozzá a `https://github.com/kovizsolt/home-assistant-timed-switch` repót
   **Integration** típussal.
3. Keresd meg a HACS-ban a **Timed Switch** integrációt, majd töltsd le.
4. Indítsd újra a Home Assistantot.
5. Nyisd meg a **Beállítások → Eszközök és szolgáltatások → Integráció
   hozzáadása** oldalt.
6. Keresd meg a **Timed Switch** integrációt, majd add hozzá.

### Kézi telepítés

1. Másold a `custom_components/timed_switch` könyvtárat a Home Assistant
   konfigurációs könyvtárába, az alábbi struktúrával:

   ```text
   <config>/custom_components/timed_switch/
   ```

2. Indítsd újra a Home Assistantot.
3. Nyisd meg a **Beállítások → Eszközök és szolgáltatások → Integráció
   hozzáadása** oldalt.
4. Keresd meg a **Timed Switch** integrációt, majd add hozzá.

Frissítéskor cseréld le a teljes `timed_switch` könyvtár tartalmát, majd indítsd
újra a Home Assistantot. A beállítások és a futási állapot a Home Assistant saját
tárolójában maradnak.

### Helyi validáció

Publikálás előtt a repó gyökeréből futtatható minden helyi ellenőrzés:

```bash
./scripts/validate.sh all
```

Az egyenként választható módok: `static`, `tests` és `hassfest`. A `hassfest`
vagy `all` módhoz adott `--no-pull` kapcsoló a már letöltött Docker image-et
használja annak frissítése nélkül.

## Konfiguráció

Az integráció kizárólag a Home Assistant felületén konfigurálható; nem kell
bejegyzést készíteni a `configuration.yaml` fájlban.

Új példány létrehozásakor add meg:

- **Név:** az eszköz és az entitások neveinek alapja;
- **ON cron-lista:** a bekapcsolási időpontok;
- **OFF cron-lista:** a kikapcsolási időpontok;
- **Manuális timeout:** a kézi felülbírálás időtartama másodpercben, alapértéke
  600; a `0` jelentése: a következő ütemezett váltásig marad kézi módban;
- **Szinkronizálási intervallum:** a célentitás ellenőrzésének periódusa
  másodpercben, alapértéke 60; a `0` kikapcsolja az ellenőrzést;
- **Alapértelmezett állapot:** a kezdőállapot, ha nincs mentett vagy
  kiértékelhető ütemezés;
- **Értesítések küldése:** ütemezett célváltáskor és korrekciós műveletkor
  tartós Home Assistant-értesítést hoz létre.

Ezután válaszd ki a vezérelt eszközt:

- **Beépített virtuális kapcsoló:** az integráció saját célkapcsolót hoz létre;
- **Meglévő entitás:** egy már létező támogatott entitást vezérel;
- **Új Virtual Switch:** új `virtual_switch` példányt készít és azt használja
  célként; ez csak akkor látható, ha a Virtual Switch integráció is telepítve van.

A beállítások később a **Beállítások → Eszközök és szolgáltatások → Timed
Switch → Konfigurálás** útvonalon módosíthatók. A célentitás módosítása teljes
integráció-újratöltést igényel; az ütemezések és időzítések élőben frissülnek.

### Cron formátum

A listák soronként vagy vesszővel elválasztva több, ötmezős `croniter`
kifejezést fogadnak. A `#` utáni rész megjegyzés. Az időpontok a Home Assistantban
beállított helyi időzónában, perc pontossággal értendők.
A rövidebb kifejezéseket a komponens jobb oldalon `*` mezőkkel egészíti ki. Az
ötödik utáni, kizárólag `*` értékű mezőket eldobja; más többletmezőnél hibát jelez.

```text
# Minden hétköznap 07:30
30 7 * * 1-5

# Minden nap 22:00
0 22 * * *
```

Ha a kapcsolónak felváltva 10 percig BE, majd 10 percig KI állapotban kell lennie,
az **ON cron-listába** kerüljön:

```text
0,20,40 * * * *
```

Az **OFF cron-listába** pedig:

```text
10,30,50 * * * *
```

Így minden óra `00`, `20` és `40` percében bekapcsol, `10`, `30` és `50` percében
kikapcsol. A ciklus óraváltáskor is folyamatos: például 00:50-kor kikapcsol, majd
01:00-kor ismét bekapcsol.

Ugyanez rövidebb, lépésközös cron jelöléssel is megadható. Az **ON cron-lista**:

```text
*/20 * * * *
```

Az **OFF cron-lista**:

```text
10-59/20 * * * *
```

A `*/20` jelentése „minden 20. percben, a 0. perctől kezdve”, ezért `00`, `20`
és `40` perckor fut. A `10-59/20` a 10. perctől induló 20 perces lépésköz, vagyis
`10`, `30` és `50` perckor fut. A két lista együtt eredményezi a 10 perc BE,
10 perc KI működést. A jelenlegi élő beállításban használt `*/10` és `5-59/10`
jelölés ugyanezt a mintát követi, de ott az állapot 5 percenként vált.

Ha mindkét lista üres, nincs automatikus váltás, és az ütemezett állapot az
alapértelmezett értéken marad.

A cron-kifejezések összeállításához és ellenőrzéséhez további segítséget a
[crontab.guru](https://crontab.guru/) oldalon találsz.

## UI megjelenítés

Az integráció egy **Timed Switch Card** nevű egyedi dashboard-kártyát tartalmaz.
Storage módban a JavaScript-erőforrás automatikusan regisztrálódik. A dashboard
szerkesztésekor válaszd a **Kártya hozzáadása → Timed Switch Card** elemet, majd
a példány `switch.<név>_expected` entitását.

YAML dashboard vagy YAML erőforrásmód esetén add hozzá kézzel:

```yaml
lovelace:
  resources:
    - url: /timed_switch/timed-switch-card.js
      type: module
```

A kártya YAML konfigurációja:

```yaml
type: custom:timed-switch-card
entity: switch.kerti_vilagitas_expected
```

A kártyán elérhető a cél-, eszköz- és ütemezett állapot, a kézi mód, az ON/OFF
ütemezés, az időzítések, a következő váltás és a diagnosztikai állapot. Ha egy
másodlagos entitás le van tiltva, a kártya a többi funkcióval tovább működik.

## Használat

Normál, **AUTO** módban az `Expected` kapcsoló követi az ütemezett állapotot, a
komponens pedig ezt érvényesíti a célentitáson. Ha a célentitást, az `Expected`
vagy a `Device` kapcsolót kézzel átbillented, a példány **MANUAL** módba kerül.
A timeout lejártakor visszatér AUTO módba és felveszi az aktuális ütemezett
állapotot.

A fontosabb létrehozott entitások (`<név>` a névből képzett azonosító):

| Entitás | Szerep |
|---|---|
| `switch.<név>_expected` | A kívánt célállapot; kézzel is vezérelhető |
| `switch.<név>_device` | A tényleges célentitás kétirányú tükre |
| `switch.<név>_timed_state` | Az ütemezett állapot; UI-ból vagy automatizálásból a következő cron-találatig felülbírálható |
| `switch.<név>_is_manual_mode` | Kézi felülbírálás be- vagy kikapcsolása |
| `number.<név>_manual_timeout` | Következő kézi felülbírálások időkorlátja |
| `number.<név>_sync_interval` | Az állapot-szinkronizálás periódusa |
| `text.<név>_on_crons`, `text.<név>_off_crons` | Az ütemezések élő szerkesztése |
| `binary_sensor.<név>_problem` | A célentitás elérhetőségi hibája |

A további szenzorok a manuális és szinkronizálási visszaszámlálást, valamint az
utolsó cél- és eszközállapot-változás idejét mutatják. A Home Assistant egyes
konfigurációs és diagnosztikai entitásokat alapból elrejthet a normál
eszköznézetből; ezek az eszköz entitáslistáján engedélyezhetők.

### Fontos viselkedés

- A `switch.<név>_timed_state` entitást külső automatizálás szabványos
  `switch.turn_on` vagy `switch.turn_off` művelettel állíthatja, például
  napfelkeltekor vagy napnyugtakor. A beállítás a következő tényleges ON/OFF
  cron-találatig, cron nélkül korlátlan ideig marad érvényben, és
  újraindítást is túlél. A percenkénti cron-ellenőrzés ezalatt is fut.

  ```yaml
  automation:
    - alias: Kerti világítás bekapcsolása napnyugtakor
      triggers:
        - trigger: sun
          event: sunset
      actions:
        - action: switch.turn_on
          target:
            entity_id: switch.kerti_vilagitas_timed_state
  ```

- MANUAL módban az ütemezés a háttérben tovább frissül, de nem írja felül az
  eszközt a timeout lejártáig.
- `manual_timeout: 0` esetén a következő ON vagy OFF ütemezési esemény zárja le
  a manuális módot.
- AUTO módban a szinkronizáló ellenőrzés kijavítja a kívánt és tényleges állapot
  eltérését. MANUAL módban nem avatkozik be.
- `unknown` vagy `unavailable` cél esetén a vezérlési logika tovább fut, a hibát
  a `Problem` bináris szenzor jelzi.
- A futási állapot újraindítás után helyreáll; a közben lejárt kézi időkorlátot
  az integráció induláskor figyelembe veszi.

## Eltávolítás

A **Beállítások → Eszközök és szolgáltatások → Timed Switch** oldalon töröld az
összes példányt, indítsd újra a Home Assistantot, majd távolítsd el a
`<config>/custom_components/timed_switch` könyvtárat. Az integráció törlése a
hozzá tartozó mentett állapotot is eltávolítja.
