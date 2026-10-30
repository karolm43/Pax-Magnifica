# Źródło i licencja — zrzut reguł tirules2.com

Ten katalog zawiera **lokalny, offline'owy zrzut reguł Twilight Imperium 4**
pobrany ze strony **https://www.tirules2.com/** (autor: Bradley / „dangothemango").

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

- `R_*.md` — tematy reguł (Living Rules Reference + noty). 109 plików.
- `F_*.md` — noty frakcyjne. 30 plików.
- `C_*.md` — noty komponentów (karty akcji, agendy, techy, jednostki...). 10 plików.
- `tirules.json` — zbiorczy zrzut strukturalny wszystkich tematów (do użycia programowego).
- `INDEX.md` — spis tematów z linkami.

## Jak odświeżyć

```powershell
# 1. pobierz pliki .php z repo tirules do katalogu tymczasowego
# 2. uruchom parser:
uv run python scripts/scrape_tirules.py <katalog_php> docs/rules_tirules
```
