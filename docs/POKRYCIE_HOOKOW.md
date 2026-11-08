# Pokrycie hooków (generowany — nie edytuj ręcznie)

Wygenerowano: `uv run python -m src.audit.hook_coverage --write`. Zasady: `RULES.md` 43.
Przypisanie do obszarów to HEURYSTYKA po słowach kluczowych (priorytetyzacja, nie decyzja).

## 1. Zarejestrowane hooki

Razem: **2**.

| Punkt zaczepienia | Rodzaj | Źródło | Komponent |
|---|---|---|---|
| `movement.enter_asteroids` | PERMIT | technology:amd | technologies:amd |
| `production.forbids` | FORBID | faction:arborec | — |

## 2. Pokrycie per kategoria

| Kategoria | Komponentów | Z hookiem | % |
|---|---:|---:|---:|
| action_cards | 143 | 0 | 0.0 |
| agendas | 63 | 0 | 0.0 |
| explores | 80 | 0 | 0.0 |
| relics | 24 | 0 | 0.0 |
| promissory_notes | 40 | 0 | 0.0 |
| galactic_events | 20 | 0 | 0.0 |
| leaders | 103 | 0 | 0.0 |
| abilities | 73 | 0 | 0.0 |
| technologies | 102 | 1 | 1.0 |
| breakthroughs | 31 | 0 | 0.0 |

## 3. Rodzaj wyzwalacza (komponenty z oknem czasowym)

| Wyzwalacz | Komponentów |
|---|---:|
| after | 78 |
| action | 76 |
| when | 69 |
| at_start | 30 |
| at_end | 12 |
| unclassified | 11 |
| before | 10 |
| during | 8 |

## 4. Zapotrzebowanie na obszary reguł (priorytety)

Im więcej komponentów dotyka obszaru, tym bardziej opłaca się domknąć jego punkty zaczepienia.

| Obszar | Komponentów | Bez hooka |
|---|---:|---:|
| planety i eksploracja (control, exploration) | 219 | 219 |
| walka (combat.*, space_cannon, bombardment) | 185 | 184 |
| produkcja (production.*) | 158 | 158 |
| ekonomia i płatności (economy, payment) | 143 | 143 |
| status i odświeżanie (status_phase) | 130 | 130 |
| ruch (movement.*) | 118 | 117 |
| karty (card_draw, promissory) | 109 | 109 |
| żetony dowodzenia (command_tokens) | 88 | 88 |
| technologie (technology) | 66 | 66 |
| agenda i głosowanie (agenda_phase) | 49 | 49 |
| cele i punkty (objectives) | 33 | 33 |
| karty strategii i inicjatywa | 26 | 26 |

Bez dopasowania do obszaru: 25 komponentów (do ręcznego przeglądu).
