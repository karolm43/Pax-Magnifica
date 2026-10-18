# Plan — Interaktywna mapa śledząca stan gry (DoD Fazy 1)

## 🎯 Cel aktu (Definition of Done)
Rozgrywasz **fizyczną partię przy stole**, a aplikacja jest:
- **interaktywną mapą** — odwzorowuje stan planszy (jednostki w systemach i na planetach,
  kontrola planet),
- **licznikiem** zasobów / punktów zwycięstwa (VP) graczy,
- **gotowa pod AI** — stan pełny, serializowalny, jednoznaczny.

Fizyczna plansza = źródło prawdy. Aplikacja odwzorowuje i cofa (Undo/God-Mode).

---

## ✅ Fundament gotowy
- `GameState` (Pydantic): `players` (VP, trade goods, commodities, technologie, planety) +
  `systems` (`space_units`, `planet_units`, `planet_owners`). Istnieje — nieużywany w UI.
- `EventStore` (SQLite, Undo/Redo/God-Mode), WebSocket live-sync.
- Mapa: grafiki kafelków, zoom/pan, sloty domowe, parser map stringów.
- Rejestr: 104 jednostki / 111 planet / 195 systemów + frakcje.

---

## 🧩 Ustalenia z danych (nie z pamięci)
- **Grafika jednostki** = `assets/units/<kolor>_<asyncId>.png`
  (kolory 3-literowe: `red, blu, grn, ylw, ppl, blk, org, pnk, tea, ...`;
  `asyncId`: `ff, dd, ca, cv, dn, fs, gf, mf, pd, sd, ws`).
- **Skróty jednostek** (DECYZJA): używamy `asyncId` 1:1 z grafikami. Przykład floty:
  `"2 dd 1 ca 4 ff"` = 2 Destroyery, 1 Cruiser, 4 Fightery.
- **Dane frakcji**: `homeSystem` (ID kafelka domowego), `startingFleet` (flota startowa),
  `startingTech`, `homePlanets`, `preferredColours`.
- **Umiejscowienie jednostek** (DECYZJA + reguła, patrz RULES.md 2b):
  - Przestrzeń (statki): ff, dd, ca, cv, dn, fs, **ws**.
  - Planeta (naziemne): **gf (infantry), mf (mech)**.
  - Planeta (struktury): **pd (PDS), sd (space dock)**.
  - ⚠️ Flagi `isShip`/`isStructure` w danych AsyncTI4 są BŁĘDNE dla mech/warsun —
    używamy jawnej tabeli reguł, nie flag.

---

## 📐 Decyzje (potwierdzone)
1. **Skróty** = `asyncId` (zgodne z grafikami).
2. **Edycja** = menu boczne (klik w kafelek → panel systemu).
3. **Setup graczy** = wybór frakcji z auto-flotą startową i planetami domowymi.
4. **Dwa stany jednostek** = przestrzeń (statki) vs planeta (naziemne + struktury).

---

## 🗺️ Plan etapowy

### Etap A — Jednostki na mapie (render stanu)
- Backend: `MapTile` wzbogacony o jednostki przestrzeni + per-planeta, z `image_url`
  jednostki (`/static/units/<kolor>_<asyncId>.png`); kolor z `PlayerState.color`.
- Frontend: render ikon statków w przestrzeni kafelka + ikon naziemnych/struktur przy
  planetach; liczniki stosów.
- Efekt: widzisz pełny skład każdego systemu (przestrzeń + planety).

### Etap B — Edytor przez menu boczne
- Klik w kafelek → panel systemu: sekcja „Przestrzeń" (statki) + sekcja per planeta
  (naziemne + struktury). Szybki wpis floty skrótami `asyncId` + przyciski +/−.
- Backend: typowane endpointy, np. `PUT /system/{pos}/space`, `PUT /system/{pos}/planet/{planet}`;
  commit do EventStore + broadcast. (God-Mode patch zostaje jako warstwa niżej.)
- Walidacja umiejscowienia: statek tylko w przestrzeni, naziemne/struktury tylko na planecie
  (wg RULES.md 2b).
- Efekt: wpisujesz, co stoi fizycznie; Undo działa.

### Etap C — Gracze: frakcje, kolory, VP, zasoby (licznik)
- Setup: przypisanie frakcji + koloru do slotu domowego. Wybór frakcji:
  - podmienia kolorowy róg na prawdziwy kafelek domowy (`homeSystem`),
  - wstawia flotę startową (`startingFleet`) i kontrolę planet domowych (`homePlanets`).
- Panel gracza: VP, trade goods, commodities, technologie — edytowalne (licznik).
- Parser `startingFleet` → jednostki w space/planet wg klasyfikacji.
- Efekt: aplikacja jest licznikiem VP/zasobów i zna skład graczy.

### Etap D — Kontrola planet (naziemne/struktury)
- Panel planety: właściciel + jednostki naziemne + struktury.
- Backend: `planet_owners`, `planet_units` (już w modelu) + endpointy + render.
- Efekt: pełny stan planszy odwzorowany.

### Etap E — Gotowość pod AI (porządek i walidacja)
- Walidacja spójności stanu (typy jednostek, gracze, umiejscowienie), eksport stanu.
- `GameState` → `FastState` (NumPy) 1:1 i bezstratnie (fundament pod Fazę 2).
- Efekt: AI czyta jednoznaczny, kompletny stan.

---

## 🧭 Rekomendowana kolejność
A (jednostki na mapie) → C (gracze/VP + frakcje) → B (edytor) → D (planety) → E (pod AI).
Każdy etap: kod + testy + QA (pytest/ruff/mypy + build) + commit.

---

## 🎨 Otwarte kwestie UI (do dopracowania w trakcie)
- Układ ikon jednostek na kafelku (stos vs grid, pozycje planet na kafelku).
- Pozycje planet: dane AsyncTI4 mają layouty planet na kafelku (pola UI) — do wykorzystania
  później, na start przybliżenie.
- Kolory graczy: na razie z `home_slots` (⚠️ założenie), docelowo z setupu gracza.
