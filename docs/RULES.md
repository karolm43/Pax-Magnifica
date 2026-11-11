# Zweryfikowane reguły Twilight Imperium 4 (źródło prawdy dla kodu)

Ten plik jest **jedynym źródłem prawdy** dla reguł TI4 implementowanych w kodzie.
Zasada projektu (spec 5.1): żadna reguła ani statystyka nie jest kodowana z pamięci.
Każda reguła poniżej ma odniesienie do oficjalnego źródła.

Status weryfikacji każdej reguły:
- ✅ **ZWERYFIKOWANE** — potwierdzone w oficjalnym Living Rules Reference (LRR) / wiki.
- ⚠️ **ZAŁOŻENIE** — zakodowane tymczasowo, wymaga potwierdzenia przez znającego grę.
- ⬜ **DO ZROBIENIA** — reguła jeszcze niezaimplementowana.

**Główne źródła** (w kolejności pierwszeństwa):
- 🥇 **tirules2.com — GŁÓWNE ŹRÓDŁO PRAWDY:** https://www.tirules2.com/
  Pełny Living Rules Reference 2.0 (PoK) + noty do Codexów (do IV, 06/2025) i wstępne
  noty do Thunder's Edge (10/2025), plus rulingi Dane Beltramiego (lead designer TI4)
  i konsensus społeczności. Każda reguła w tym pliku jest weryfikowana najpierw tutaj;
  tematy mają osobne podstrony (np. „Anomalies", „Movement", „Space Combat").
  Pozostałe źródła są pomocnicze/backup.
- 📁 **LOKALNY ZRZUT (offline, najszybszy):** [`docs/rules_tirules/`](rules_tirules/INDEX.md)
  — kompletny zrzut tirules2.com (149 tematów: 109 reguł, 30 frakcji, 10 komponentów)
  w Markdown + `tirules.json`. **Sprawdzaj reguły TUTAJ w pierwszej kolejności** (bez
  requestów online). Odświeżenie i atrybucja: [`docs/rules_tirules/SOURCE.md`](rules_tirules/SOURCE.md).
  Gdy lokalny zrzut nie wystarcza, zajrzyj na żywą stronę tirules2.com.
  > **To są ZASADY i DOPRECYZOWANIA reguł** (edge-case'y, interakcje, rulingi Dane) —
  > NIE opisy działania umiejętności frakcji/kart. Pełne opisy komponentów są w assetach
  > JSON AsyncTI4; pliki `F_*`/`C_*` zawierają tylko noty-doprecyzowania (patrz `SOURCE.md`).
- Living Rules Reference 2.0 (Prophecy of Kings), FFG, 09/2020 —
  [PDF](https://images-cdn.fantasyflightgames.com/filer_public/51/55/51552c7f-c05c-445b-84bf-4b073456d008/ti10_pok_living_rules_reference_20_web.pdf)
- TI Wiki (odzwierciedla LRR): https://twilight-imperium.fandom.com/wiki/Anomalies

> Uwaga: wszystkie reguły mogą być nadpisane przez karty i zdolności specjalne
> (frakcje, technologie, karty akcji). To obsługujemy przez `rules_hooks` (asymetria).

---

## Spis treści (sekcje w osobnych plikach)

RULES.md jest INDEKSEM. Treść każdej sekcji leży w `docs/rules/R<nr>.md` (numeracja bez zmian, więc
odwołania typu „RULES.md 43.1a” czytaj w pliku `rules/R43.md`). Podsekcje 2a–2e są w `R02.md`, 3a w `R03.md`.
Czytaj WYŁĄCZNIE plik potrzebnej sekcji. Nową regułę dopisuj do pliku jej sekcji (albo nowy `R<nr>.md` + wiersz tu).

| # | Sekcja | Linii |
|---|---|---:|
| 1 | [Anomalie (Anomalies)](rules/R01.md) | 48 |
| 2 | [Sąsiedztwo i wormhole (Adjacency)](rules/R02.md) | 220 |
| 3 | [Ruch (Movement)](rules/R03.md) | 60 |
| 4 | [Pozycje stat-area (player-stats heksy)](rules/R04.md) | 26 |
| 5 | [Startowe żetony dowodzenia (command counters)](rules/R05.md) | 13 |
| 6 | [Fazy gry — mapowanie na format frontendu](rules/R06.md) | 15 |
| 7 | [Ekonomia planet: optimal / flex](rules/R07.md) | 13 |
| 8 | [Liderzy frakcji (agent/commander/hero)](rules/R08.md) | 12 |
| 9 | [Kolejność tur fazy akcji i pas](rules/R09.md) | 19 |
| 10 | [Posiadane jednostki i ulepszenia (unitsOwned)](rules/R10.md) | 45 |
| 11 | [Klucz tożsamości gracza w web-data (desync panel↔mapa)](rules/R11.md) | 23 |
| 12 | [Kontrola planet — jedno źródło prawdy (opcja A)](rules/R12.md) | 21 |
| 13 | [Faza strategii (wybór kart strategii)](rules/R13.md) | 79 |
| 14 | [Źródła danych: codexy + thunders_edge, dedup erraty](rules/R14.md) | 59 |
| 15 | [Typ planety: pole `planetTypes` (lista) vs `planetType`](rules/R15.md) | 17 |
| 16 | [Wybór technologii startowej frakcji](rules/R16.md) | 49 |
| 17 | [Systemy domowe poza planszą: Ghost of Creuss, Crimson Rebellion](rules/R17.md) | 27 |
| 18 | [Panel gracza: zdolności, technologie frakcyjne, przełomy](rules/R18.md) | 38 |
| 19 | [Akcja taktyczna: aktywacja systemu + maszyna kroków](rules/R19.md) | 41 |
| 20 | [Walka: pomoce liczbowe (asystent, nie sędzia)](rules/R20.md) | 32 |
| 21 | [Przejęcie kontroli planety (inwazja)](rules/R21.md) | 18 |
| 22 | [Produkcja: pomoc liczbowa (koszt + zasoby)](rules/R22.md) | 19 |
| 23 | [Kontrola planety przy stawianiu jednostek (auto)](rules/R23.md) | 28 |
| 24 | [Kolejność graczy: seating order, speaker, wybór kart strategii](rules/R24.md) | 38 |
| 25 | [Drag-and-drop przenoszenia jednostek (UI/God-Mode)](rules/R25.md) | 40 |
| 26 | [Umiejscowienie jednostek przy przenoszeniu: statek↔przestrzeń, naziemne↔planeta](rules/R26.md) | 38 |
| 27 | [Wyczerpywanie komponentów: planety, technologie, liderzy (exhaust/ready)](rules/R27.md) | 45 |
| 28 | [Grywalne frakcje vs placeholdery systemowe (Neutral/Lazax)](rules/R28.md) | 50 |
| 29 | [ZMIANA KIERUNKU: silnik-SĘDZIA + okna czasowe (zastępuje "asystent, nie sędzia")](rules/R29.md) | 85 |
| 30 | [Akcja strategiczna: primary + okno secondary](rules/R30.md) | 184 |
| 31 | [Walidacja przepływu fazy akcji + aktywny gracz (twarda egzekucja)](rules/R31.md) | 287 |
| 32 | [Ruch statków: egzekucja legalności (akcja taktyczna)](rules/R32.md) | 99 |
| 33 | [Walidacja aktywacji i produkcji (twarda egzekucja)](rules/R33.md) | 103 |
| 34 | [Specyfikacja czasowa komponentów: wyzwalacz → typ okna](rules/R34.md) | 21 |
| 35 | [Spójność referencji: placeholder `<color>` promissory notes jako SZABLON](rules/R35.md) | 31 |
| 36 | [Limity rąk i zbiór poziomów trudności bota](rules/R36.md) | 48 |
| 37 | [Wyniki audytu danych (baseline, luki referencyjne, założenia)](rules/R37.md) | 92 |
| 38 | [Space Cannon Offense: kolejność, zasięg (Deep Space Cannon), rzuty, straty](rules/R38.md) | 67 |
| 39 | [Walka (kosmiczna i naziemna): rundy, AFB, rzuty, Sustain Damage, straty](rules/R39.md) | 125 |
| 40 | [Inwazja: Bombardment, Commit, Space Cannon Defense, walka naziemna, Establish Control](rules/R40.md) | 35 |
| 41 | [Faza statusu, cele publiczne/tajne, punkty zwycięstwa](rules/R41.md) | 46 |
| 42 | [Fleet pool: limit statków w systemie i usuwanie nadwyżki](rules/R42.md) | 35 |
| 43 | [Asymetria i wyjątki (frakcje, karty akcji, agendy): zasady architektury hooków](rules/R43.md) | 172 |
| 44 | [Gra sieciowa (do 6 graczy): tożsamość, autoryzacja, widoczność, zasada `actor_id`](rules/R44.md) | 66 |
| 45 | [Setup startowy: tajne cele, notki, żeton Custodians, cele publiczne](rules/R45.md) | 27 |
| 46 | [Eksploracja planet po przejęciu kontroli](rules/R46.md) | 41 |
| 47 | [Transakcje między graczami + żetony długu (debt)](rules/R47.md) | 36 |
| 48 | [Koniec gry: limit rund i epilog (głosowanie honorowe / niehonorowe)](rules/R48.md) | 18 |
| 49 | [Badanie technologii + karta Technology](rules/R49.md) | 45 |
| 50 | [Thunder's Edge: ekspedycje, The Fracture, Thunder's Edge](rules/R50.md) | 74 |
| 51 | [Faza agendy: ujawnienie, głosowanie, wynik, planety](rules/R51.md) | 34 |
| 52 | [Żeton Custodians: zdjęcie w inwazji na Mecatol Rex](rules/R52.md) | 25 |
| 53 | [Zagrywanie kart akcji (okno ACTION) + efekty jako hooki](rules/R53.md) | 64 |
| 54 | [Baza zdarzeń i okien czasowych (silnik zdarzeń)](rules/R54.md) | 19 |
| 55 | [Technologie ogólne jako hooki](rules/R55.md) | 32 |
| 56 | [Decyzje graczy i oferty technologii (nigdy automatycznie) — decyzja użytkownika 2026-11-09](rules/R56.md) | 12 |
| 57 | [Technologie z akcją, zdolności poza akcją, frontier i produkcja „wolna” — decyzja użytkownika 2026-11-09](rules/R57.md) | 28 |
| 58 | [Zegar szachowy graczy](rules/R58.md) | 31 |
