# Źródło i licencja — zrzut reguł tirules2.com

Ten katalog zawiera **lokalny, offline'owy zrzut reguł Twilight Imperium 4**
pobrany ze strony **https://www.tirules2.com/** (autor: Bradley / „dangothemango").

## ⚠️ Czym to JEST, a czym NIE JEST (czytaj najpierw)

**To są ZASADY i DOPRECYZOWANIA reguł TI4** — oficjalny tekst Living Rules Reference 2.0
plus **noty, interpretacje i edge-case'y**: jak dana reguła działa w szczególnych,
niejednoznacznych sytuacjach i jak wchodzi w interakcję z innymi regułami/kartami.
To warstwa „jak sędzia rozstrzyga brzegowe przypadki".

**To NIE SĄ opisy działania umiejętności frakcji ani kart.** Pełne teksty umiejętności
(co robi dana zdolność frakcji, karta akcji, technologia, lider, promissory itd.)
**są już w assetach JSON AsyncTI4** (`assets/data/...`) i to one są źródłem opisów
komponentów. Pliki `F_*` / `C_*` w tym katalogu zawierają TYLKO **noty-doprecyzowania**
do tych komponentów (np. „co się dzieje, gdy X nakłada się na Y", „czy ability triggeruje
w oknie Z"), a NIE ich podstawowy opis. Dlatego w sekcjach bywają puste nagłówki
(komponent bez żadnych brzegowych uwag = brak noty, ale pełny opis jest w JSON).

**Jak tego używać w silniku:** reguła ogólna i jej doprecyzowanie → stąd (tirules).
Treść/parametry konkretnej karty czy zdolności frakcji → z assetów JSON. Dane liczbowe
(statystyki jednostek, koszty, wartości planet) → z assetów JSON, nigdy stąd.

## Pochodzenie

- **Strona:** https://www.tirules2.com/
- **Repozytorium źródłowe:** https://github.com/dangothemango/tirules
- Treść pobrana z plików `R_*.php` / `F_*.php` / `C_*.php` tego repo (czyste fragmenty
  HTML) i przekonwertowana do Markdown + JSON skryptem `scripts/scrape_tirules.py`.
- Data zrzutu: 2026-10-30. Źródło odzwierciedla **Living Rules Reference 2.0** (PoK),
  z notami do **Codexów I–IV** (06/2025) i wstępnymi notami do **Thunder's Edge** (10/2025).

## Licencja i prawa

- **Kod/struktura repo tirules:** licencja **GPL-3.0** (patrz repo źródłowe).
- **Treść reguł Twilight Imperium:** **© Fantasy Flight Games**. Strona tirules2.com
  jest nieoficjalna („Not Affiliated") i nie jest powiązana z FFG ani z tirules.com.
- Noty oznaczone `_[Dane ruling]_` to oficjalne rulingi Dane Beltramiego (lead designer
  TI4), spoza samego Living Rules Reference — na stronie wyróżnione kolorem (`class="ruling"`).

Materiał użyty tu wyłącznie jako wewnętrzne źródło referencyjne reguł dla silnika
Custodian Engine. W razie publikacji projektu zachowaj tę atrybucję.

## Struktura

- `R_*.md` — tematy reguł (Living Rules Reference + noty-doprecyzowania). 109 plików.
- `F_*.md` — noty-doprecyzowania frakcji (edge-case'y zdolności, NIE pełne opisy). 30 plików.
- `C_*.md` — noty-doprecyzowania komponentów (karty akcji, agendy, techy, jednostki, relikty,
  cele, promissory, eksploracja, legendarne planety, eventy). NIE pełne opisy kart. 10 plików.
- `tirules.json` — zbiorczy zrzut strukturalny wszystkich tematów (do użycia programowego).
- `INDEX.md` — spis tematów z linkami.

### Format pozycji (MD i JSON)

Noty to listy (często wielopoziomowe, z zachowanymi podpunktami). Oznaczenia:
- `_[Dane ruling]_` (MD) / `"dane_ruling": true` (JSON) — oficjalny ruling Dane Beltramiego,
  spoza samego LRR.
- `**Etykieta**` (MD) / `"subheading": true` (JSON) — śródtytuł grupy w sekcji LRR
  (np. „Costs", „Timing"), nie osobna reguła.
- akapit bez myślnika (MD) / `"paragraph": true` (JSON) — tekst wstawiony między pozycje listy.

## Jak odświeżyć

```powershell
# 1. pobierz pliki .php z repo tirules do katalogu tymczasowego
# 2. uruchom parser:
uv run python scripts/scrape_tirules.py <katalog_php> docs/rules_tirules
```
