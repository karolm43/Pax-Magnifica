# Pokrycie hooków (generowany — nie edytuj ręcznie)

Wygenerowano: `uv run python -m src.audit.hook_coverage --write`. Zasady: `RULES.md` 43.
Obszary reguł i typ hooka to HEURYSTYKA po słowach kluczowych (priorytetyzacja, nie decyzja).

Zarejestrowanych hooków: **176** (lista: `pokrycie_hookow/hooki.md`).

## 2. Pokrycie per kategoria

| Kategoria | Komponentów | Z hookiem | % |
|---|---:|---:|---:|
| action_cards | 143 | 143 | 100.0 |
| agendas | 123 | 0 | 0.0 |
| explores | 80 | 4 | 5.0 |
| relics | 24 | 23 | 95.8 |
| promissory_notes | 41 | 10 | 24.4 |
| galactic_events | 20 | 0 | 0.0 |
| planets | 19 | 19 | 100.0 |
| leaders | 103 | 15 | 14.6 |
| abilities | 73 | 9 | 12.3 |
| technologies | 102 | 46 | 45.1 |
| breakthroughs | 31 | 5 | 16.1 |
| units | 90 | 11 | 12.2 |

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

## 4. Zapotrzebowanie na obszary reguł i typy hooków (priorytety)

Im więcej komponentów dotyka obszaru, tym bardziej opłaca się domknąć jego punkty zaczepienia.

| Obszar | Komponentów | Bez hooka |
|---|---:|---:|
| planety i eksploracja (control, exploration) | 280 | 207 |
| walka (combat.*, space_cannon, bombardment) | 247 | 149 |
| produkcja (production.*) | 196 | 123 |
| ekonomia i płatności (economy, payment) | 185 | 145 |
| status i odświeżanie (status_phase) | 162 | 106 |
| karty (card_draw, promissory) | 153 | 113 |
| ruch (movement.*) | 149 | 107 |
| żetony dowodzenia (command_tokens) | 117 | 85 |
| agenda i głosowanie (agenda_phase) | 98 | 75 |
| technologie (technology) | 80 | 59 |
| cele i punkty (objectives) | 48 | 34 |
| karty strategii i inicjatywa | 48 | 33 |

Szacowany typ hooka (RULES.md 43.1 pkt 4):

| Typ | Komponentów |
|---|---:|
| — | 259 |
| PERMIT (pozwolenie) | 197 |
| TRIGGER (okno reakcji) | 157 |
| MODIFY (liczba/rzut) | 129 |
| FORBID (zakaz) | 60 |
| REPLACE (instead of) | 47 |

## 6. Kolejka kart ACTION do zrobienia (0)

Karty zagrywane jako akcja komponentu, które silnik zagrywa tylko ręcznie (odrzucenie bez efektu). Po dodaniu efektu karta znika z tej listy.

| Id | Nazwa | Źródło | Typ (szac.) | Obszary | Tekst |
|---|---|---|---|---|---|

## 7. Frakcje (komponenty frakcyjne i pokrycie)

Zdolności, technologie frakcyjne, liderzy, przełom i promissory notes przypisane do frakcji. Keleres (3 warianty) liczony jako jedna rodzina.

| Frakcja | Zdolności | Tech. | Liderzy | Przełom | PN | Jedn. | Z hookiem / razem | Obszary reguł |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| The Arborec (`arborec`) | 1 | 2 | 3 | 1 | 1 | 3 | 10 / 11 | planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Argent Flight (`argent`) | 2 | 2 | 3 | 1 | 1 | 3 | 0 / 12 | agenda i głosowanie, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| Last Bastion (`bastion`) | 3 | 2 | 4 | 1 | 1 | 4 | 0 / 15 | ekonomia i płatności, karty, planety i eksploracja, produkcja, status i odświeżanie, walka, żetony dowodzenia |
| The Ghosts of Creuss (`creuss`) | 3 | 2 | 3 | 1 | 1 | 2 | 0 / 12 | planety i eksploracja, produkcja, ruch, status i odświeżanie, walka |
| The Deepwrought Scholarate (`deepwrought`) | 2 | 2 | 3 | 1 | 1 | 2 | 0 / 11 | ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie |
| The Empyrean (`empyrean`) | 3 | 2 | 3 | 1 | 2 | 2 | 0 / 13 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Firmament (`firmament`) | 2 | 2 | 3 | 1 | 1 | 2 | 0 / 11 | cele i punkty, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Emirates of Hacan (`hacan`) | 3 | 2 | 3 | 1 | 1 | 2 | 0 / 12 | agenda i głosowanie, ekonomia i płatności, karty, karty strategii i inicjatywa, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Universities of Jol-Nar (`jol-nar`) | 3 | 2 | 3 | 1 | 1 | 2 | 12 / 12 | ekonomia i płatności, karty strategii i inicjatywa, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka |
| The Council Keleres - Mentak (`keleres`) | 3 | 3 | 5 | 1 | 4 | 2 | 0 / 18 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The L1Z1X Mindnet (`l1z1x`) | 2 | 2 | 3 | 1 | 1 | 3 | 0 / 12 | ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Barony of Letnev (`letnev`) | 2 | 2 | 3 | 1 | 1 | 2 | 11 / 11 | ekonomia i płatności, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Mahact Gene-Sorcerers (`mahact`) | 3 | 2 | 3 | 1 | 1 | 4 | 0 / 14 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Mentak Coalition (`mentak`) | 2 | 2 | 3 | 1 | 1 | 3 | 0 / 12 | ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka |
| The Embers of Muaat (`muaat`) | 2 | 2 | 3 | 1 | 1 | 4 | 0 / 13 | ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Naalu Collective (`naalu`) | 2 | 2 | 4 | 1 | 1 | 5 | 0 / 15 | agenda i głosowanie, ekonomia i płatności, karty, karty strategii i inicjatywa, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Naaz-Rokha Alliance (`naaz-rokha`) | 2 | 2 | 3 | 1 | 1 | 5 | 0 / 14 | ekonomia i płatności, karty, karty strategii i inicjatywa, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Nekro Virus (`nekro`) | 3 | 4 | 3 | 1 | 1 | 2 | 0 / 14 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Nomad (`nomad`) | 2 | 2 | 5 | 1 | 1 | 3 | 0 / 14 | ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Ral Nel Consortium (`ral nel`) | 2 | 2 | 3 | 1 | 1 | 4 | 0 / 13 | karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Crimson Rebellion (`rebellion`) | 3 | 2 | 6 | 1 | 1 | 4 | 0 / 17 | ekonomia i płatności, produkcja, ruch, status i odświeżanie, walka |
| The Clan of Saar (`saar`) | 2 | 2 | 3 | 1 | 1 | 3 | 0 / 12 | cele i punkty, ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka |
| Sardakk Norr (`sardakk`) | 1 | 2 | 3 | 1 | 1 | 3 | 11 / 11 | karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka, żetony dowodzenia |
| The Federation of Sol (`sol`) | 2 | 2 | 3 | 1 | 1 | 3 | 11 / 12 | ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Titans of Ul (`ul`) | 3 | 2 | 3 | 1 | 1 | 4 | 0 / 14 | ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka |
| The Vuil'raith Cabal (`vuil'raith`) | 3 | 2 | 3 | 1 | 1 | 4 | 0 / 14 | ekonomia i płatności, planety i eksploracja, produkcja, ruch, status i odświeżanie, technologie, walka |
| The Winnu (`winnu`) | 2 | 2 | 3 | 1 | 1 | 2 | 0 / 11 | ekonomia i płatności, karty strategii i inicjatywa, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Xxcha Kingdom (`xxcha`) | 2 | 2 | 4 | 1 | 1 | 2 | 0 / 12 | agenda i głosowanie, ekonomia i płatności, karty, planety i eksploracja, produkcja, ruch, status i odświeżanie, walka, żetony dowodzenia |
| The Yin Brotherhood (`yin`) | 2 | 2 | 3 | 1 | 1 | 2 | 0 / 11 | cele i punkty, ekonomia i płatności, planety i eksploracja, produkcja, status i odświeżanie, technologie, walka |
| The Yssaril Tribes (`yssaril`) | 3 | 2 | 3 | 1 | 1 | 2 | 0 / 12 | cele i punkty, karty, planety i eksploracja, ruch, status i odświeżanie |

## Spis plików szczegółowych (czytaj punktowo, tylko gdy potrzebne)

- [`pokrycie_hookow/hooki.md`](pokrycie_hookow/hooki.md) — sekcja 1: zarejestrowane hooki i punkty zaczepienia.
- [`pokrycie_hookow/przypadki_szczegolne.md`](pokrycie_hookow/przypadki_szczegolne.md) — sekcja 5: komponenty bez dopasowania do obszaru.
- [`pokrycie_hookow/szczegoly_action_cards.md`](pokrycie_hookow/szczegoly_action_cards.md) — sekcja 8: action_cards (143 / 143 z hookiem).
- [`pokrycie_hookow/szczegoly_agendas.md`](pokrycie_hookow/szczegoly_agendas.md) — sekcja 8: agendas (0 / 123 z hookiem).
- [`pokrycie_hookow/szczegoly_explores.md`](pokrycie_hookow/szczegoly_explores.md) — sekcja 8: explores (4 / 80 z hookiem).
- [`pokrycie_hookow/szczegoly_relics.md`](pokrycie_hookow/szczegoly_relics.md) — sekcja 8: relics (23 / 24 z hookiem).
- [`pokrycie_hookow/szczegoly_promissory_notes.md`](pokrycie_hookow/szczegoly_promissory_notes.md) — sekcja 8: promissory_notes (10 / 41 z hookiem).
- [`pokrycie_hookow/szczegoly_galactic_events.md`](pokrycie_hookow/szczegoly_galactic_events.md) — sekcja 8: galactic_events (0 / 20 z hookiem).
- [`pokrycie_hookow/szczegoly_planets.md`](pokrycie_hookow/szczegoly_planets.md) — sekcja 8: planets (19 / 19 z hookiem).
- [`pokrycie_hookow/szczegoly_leaders.md`](pokrycie_hookow/szczegoly_leaders.md) — sekcja 8: leaders (15 / 103 z hookiem).
- [`pokrycie_hookow/szczegoly_abilities.md`](pokrycie_hookow/szczegoly_abilities.md) — sekcja 8: abilities (9 / 73 z hookiem).
- [`pokrycie_hookow/szczegoly_technologies.md`](pokrycie_hookow/szczegoly_technologies.md) — sekcja 8: technologies (46 / 102 z hookiem).
- [`pokrycie_hookow/szczegoly_breakthroughs.md`](pokrycie_hookow/szczegoly_breakthroughs.md) — sekcja 8: breakthroughs (5 / 31 z hookiem).
- [`pokrycie_hookow/szczegoly_units.md`](pokrycie_hookow/szczegoly_units.md) — sekcja 8: units (11 / 90 z hookiem).
