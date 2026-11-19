# Postęp projektu — Custodian Engine

Plik śledzi stan prac między sesjami. Aktualizowany na koniec każdego bloku.
Starsze, ukończone bloki (Faza 1 → bloki do 2026-11-18) są w `PROGRESS_ARCHIWUM.md` (czytaj punktowo).

> **Aktualny etap:** E8 (silnik-SĘDZIA) + hooki: karty, relikty, technologie ogólne, cele, karty strategii,
> agendy ✅; frakcje (Fala 2) w toku; bot: B0–B1, B3 ✅, B2 rdzeń, następne B2 (bench) / B5 (`docs/bot/PLAN.md`).
> Stan pokrycia: `POKRYCIE_HOOKOW.md` (generowany). Reguły: `RULES.md` 29, 43, 53, 65.

## Status etapów silnika

| Etap | Zakres | Status |
|---|---|---|
| Faza 1 | Cyfrowa plansza + God-Mode (dane, mapa, setup, edycja, Undo) | ✅ ukończona |
| F0–F18 | Migracja na frontend ti4_web + panele graczy + God-Mode UI | ✅ ukończone |
| E1–E2 | Fazy + kolejność tur + faza strategii | ✅ ukończone |
| E3 | Akcja taktyczna (aktywacja, ruch, walka, inwazja, produkcja) | ✅ fundament |
| E4 | Kontrola komponentów (exhaust/refresh) + menu RMB | ✅ ukończone |
| S | Karty strategii 1–8: primary + secondary (`core/strategy_cards/`) | ✅ ukończone |
| E8 | Silnik-SĘDZIA: walidacja reguł + okna czasowe (T1–T7 + faza akcji 31.7/31.8, audyt 31.9) | 🔧 w toku |
| C | Punkty centralne C1–C9 (strażnik architektury) | ✅ ukończone |
| H1–H3 | Hooki: rejestr, punkty MODIFY/PERMIT/FORBID, raport pokrycia | ✅ ukończone |
| H1b | Reakcje z cofnięciem: hold-play (Sabotage) + hold-rewind (HOLD) | ✅ (RULES.md 53.6, 53.7) |
| H4 | Karty akcji: ACTION + reakcje w oknach + przeciąganie z ręki | ✅ 143/143 |
| — | Relikty (23/23 aktywnych), technologie ogólne (33/33), cele (80/80 automatycznie) | ✅ |
| E6 | Faza agendy (głosowanie, remis, prawa); efekty agend | ✅ cała faza + efekty talii oficjalnej (50/50); ⬜ Absol (60) |
| H5 | Frakcje: zdolności, liderzy, notki, przełomy, technologie frakcyjne | ⬜ (technologie 36/102) |
| N | Sieć: N0 `actor_id` ✅, N1 tokeny ✅, N2 projekcja ✅, N3 zapis ✅, N5 część 1 ✅; N4 współbieżność ⬜ | 🔧 |
| QA | pytest-xdist/testmon, E2E Playwright (solo + host/gość) | ✅ |

**Następne kroki (kolejność):** efekty agend Absol → hooki at_start/at_end/during (16 zdarzeń jeszcze nieemitowanych,
`OKNA_CZASOWE.md`) → frakcje (zdolności, liderzy, promissory notes) → N4/N5 część 2 → bot.

> Pełna historia ukończonych bloków ze szczegółami: `PROGRESS_ARCHIWUM.md`.


## 2026-11-18 — Fuzzer partii botów + luki generatora ruchów

- ✅ `tests/engine/fuzz.py`: losowe partie botów przez prawdziwe API
  (`uv run python -m tests.engine.fuzz --games 300 --rounds 5`, `--replay <ziarno>`). Losowe frakcje
  (3–6, jeden wariant z rodziny), bot losowy, losowa kolejność pytanych graczy, 50% partii z agendą.
  Po każdym ruchu: zgodność katalog ↔ HTTP, niezmienniki stanu (`check_invariants`), JSON round-trip
  i dokument web-data dla każdego gracza (to, co czyta front). Błąd = `fuzz_reports/fuzz_seed<N>.json`
  (ziarno, ostatnie akcje, traceback, migawka stanu); podsumowanie grupuje błędy po sygnaturze.
- `BotTable` (`tests/engine/driver.py`): wstrzykiwana polityka kolejności kandydatów, kolejność graczy
  i hook po kroku (bot pasywny bez zmian).
- ✅ Luki generatora znalezione fuzzerem (gra stawała): produkcja z Construction (krok `choose_dock`)
  i z secondary Warfare TE → nowa akcja `production_skip` („Finish production”,
  `/tactical/production/skip-grant`); obowiązkowa technologia z Research Grant Reallocation (wejście
  `research` w trybie GAIN → pierwsza dostępna); okno FLEET_POOL (np. po Clandestine Operations) → nowa
  akcja `fleet_pool_resolve` z podpowiedzią `core/fleet_pool.auto_removal`.
- Testy: zgodność HTTP obu nowych akcji (`test_actions_parity`), parametry GAIN (`test_legal_windows`),
  smoke fuzzera na stałych ziarnach (`test_fuzz_games`).
- Zakres fuzzera = zakres generatora: bez akcji taktycznej, walki i kart akcji (B5) — wejdą pod fuzzer
  automatycznie. Błędy UI: następny krok to odtwarzanie zapisanych stanów w przeglądarce (Playwright).
- QA: pytest `tests/engine` ✓, ruff ✓, mypy ✓. Pełny pytest i front pominięte (zmiana tylko
  w warstwie bota i testach). Wymaga restartu backendu (nowe akcje bota).

## Poprawki UI: ikona producenta Magmus Reactor, szary Avernus, Custodians najniżej (XI 2026)

- Okno produkcji: producent spoza jednostek dostaje `kind`/`sourceId` (`Producer.source` = HookSource
  hooka `POINT_PRODUCTION_SYSTEM_VALUE`) — Magmus Reactor pokazuje ikonę koloru technologii i jej
  nazwę zamiast pustego sprite'a „system”; planety-producenci (Custodian's Favour, Aerie Hololattice)
  ikonę planety.
- Wyczerpany żeton-planeta (Avernus) szarzeje cały (filtr na sprite w `Token.tsx`), okrąg planety
  go już nie przyciemnia częściowo.
- Żeton Custodians (`custodian`, `custodianvp`) ma z-index 2 — przykrywa go wszystko na kafelku.
- QA: pytest `-k "production or muaat"` ✓, ruff ✓, mypy ✓ (zmienione pliki), tsc ✓, eslint ✓,
  vitest production/map/utils ✓. Pełny pytest, build i e2e pominięte. Wymaga restartu backendu (nowe pola).

## 2026-11-19 — Okna reakcji: deklaracje pasu, wyciszenia, szybkie okna (RULES.md 54.12)

- ✅ `core/reaction_prefs.py`: prywatne deklaracje pasu per kategoria okna (`all`, `strategy`, `agenda`,
  `combat`, `sabotage`) z czasem trwania (`turn`/`round`/`agenda`/`combat`/`always`), „Ask me only when it
  concerns me” (`involved` liczone z informacji jawnej), wyciszone karty reakcji (po nazwie) i oferty
  „you may” (klucz `covers`; obowiązkowych nie da się wyciszyć). Wygasłe deklaracje czyści `step_settle`.
- „Quick windows” hosta (`GameState.quick_reaction_windows`, `POST /reaction-settings/quick`): okno kończy
  się, gdy wszyscy spasowali (`reaction_window.settle_quick`). Domyślna długość okna 4 → 5 s.
- UI: panel „Reactions” w `TurnControls` (`ReactionSettings`, zastępuje `ReactionAutoPassToggle`),
  „Never ask” w ofertach i prośbach o reakcję z ręki, ustawienie hosta w Ustawieniach;
  zminimalizowane okna jako przesuwalna pigułka `DraggablePill`.
- Testy: `tests/test_reaction_prefs.py`, `test_reaction_window.py`, `test_reaction_pause.py`, vitest
  `ReactionSettings`, `OfferNeverAsk`, `DraggablePill`.

## 2026-11-19 — B5: bot prowadzi akcję taktyczną + bot losowy (RULES.md 65.8)

- ✅ Katalog akcji podzielony: `engine/action_base.py` (kontekst, baza, kontrola aktora),
  `engine/actions_tactical.py` (aktywacja, ruch, produkcja, walka, odwrót, Space Cannon, inwazja,
  eksploracja, pojemność, karty akcji ACTION) + mapowanie HTTP w `api/bot_http.py`;
  generator wariantów `engine/legal_tactical.py` (pierwszy kandydat = ruch bezpieczny).
- `engine_config.json`: wszystkie poziomy trudności na `random` (do testów, decyzja użytkownika).
- Losowa frakcja (setup, kreator, fuzzer) najpierw z frakcji zrobionych (`core/faction_support`);
  znacznik „Ready” w kreatorze (tymczasowy). Wybór technologii startowych w kreatorze = karty `TechCard`.
- ✅ Błąd znaleziony fuzzerem (ziarno 11, gra stawała): „Finish production” z secondary Warfare w trakcie
  okna FLEET_POOL nie widziało okna secondary; po zamknięciu okna limitu (FLEET_POOL / CAPACITY)
  `strategic_action.resume_after_limit_window` kończy odpowiedź respondenta. Test w `tests/test_fleet_pool.py`.
- Strażnik `test_actions_parity`: rodzaje B5 jawnie w `NOT_YET_COVERED` („tylko fuzzer”) — celowane
  scenariusze zgodności HTTP do dopisania. Smoke fuzzera w pytest skrócony do 2 rund.
- Bot nie używa zdolności „may” wewnątrz kroków ani kart reakcji (okna reakcji botów pasuje silnik).

## 2026-11-19 — B11: The Clan of Saar (RULES.md 62.14)

- ✅ `core/hooks/factions/saar.py`: Scavenge, Nomadic, Floating Factory I/II (punkt centralny struktury
  pływającej `core/floating_structures.py`: dok w przestrzeni, ruch/odwrót jak statek, zniszczenie przy
  blokadzie), Chaos Mapping, Captain Mendosa, Rowl Sarrig, Gurno Aggero, Scavenger Zeta, Ragh's Call,
  Deorbit Barrage. Zmiany punktowe w `unit_ops`, `movement`, `retreat`, `tactical`, `objectives`,
  `board_edit`, `visibility`, `neighbors`.
- Setup: planety domowe przez `control.assign_home_planet` — bez zdarzenia `PLANET_CONTROL_GAINED`
  (Scavenge nie daje TG za dom), punkt centralny kontroli zachowany (z lustrem `controlled_planets`).
- Armageddon Relay: efekt na planszy (`heroBoardFx.ts`, fala z systemów z jednostkami Saar).
- Rulingi `F_saar` z testami (`tests/factions/test_saar.py`, scenariusze `test_flows_saar.py`); odroczone:
  scavenge 2.2 (Naaz-Rokha), floating-factory 8.1 (Nekro) w `tests/rulings_status.json`.
- QA (całość bloku 2026-11-19): pytest pełny ✓ (engine osobno), ruff ✓, mypy ✓, tsc ✓, eslint (zmienione) ✓,
  vitest offers/game-shell/settings/setup/shared/player/strategy/cards ✓, build ✓. e2e pominięte.
  Fuzzer: tylko 4 ziarna smoke (duża próba pominięta - za długa). Wymaga restartu backendu (nowe trasy i pola).

## 2026-11-19 — „No whens” / „No afters” w oknie Rady; bot bada technologie

- ✅ Połowiczne deklaracje agendy `agenda_when` / `agenda_after` (RULES.md 54.12): `reaction_prefs.skipped_moments`,
  `reaction_window.has_playable_reaction(skip_moments=...)` - karta akcji/notka pasująca tylko do okien
  z zadeklarowanym momentem nie liczy się; obie połowy = pas na całą agendę; zmiana w trakcie okna pasuje od
  razu (`pass_open_windows(..., registry)`).
- UI: `AgendaPassButtons` w oknie Rady (krok VOTE), deklaracja na bieżącą agendę; szersza deklaracja z panelu
  Reactions wciska obie połowy.
- ✅ Bot (RULES.md 65.8): primary i secondary karty Technology - warianty badania z zapłatą
  (`engine/legal.research_payloads`), wcześniej bot zawsze rezygnował.
- Scalanie okien before/after wokół jednego zdarzenia: poza agendą (już jedna pauza when+after) - nie ruszane.
- QA: pytest engine + reakcje/agendy/jolnar ✓, ruff ✓, mypy ✓ (zmienione), tsc ✓, eslint ✓, vitest agenda +
  ReactionSettings ✓. Duża próba fuzzera pominięta (puszcza użytkownik). Wymaga restartu backendu.

## 2026-11-19 — B11: The Naaz-Rokha Alliance (RULES.md 62.15)

- ✅ `core/hooks/factions/naaz.py`: Distant Suns, Fabrication, Black Market Forgery, Pre-Fab Arcologies,
  Supercharge, Visz El Vir, Eidolon / Z-Grav Eidolon, Garv and Gunn, Dart and Tai, Hesh and Prit (Perfect
  Synthesis), Absolute Synergy + Eidolon Maximum.
- Rdzeń (punkty ogólne, bez nazw frakcji):
  - Eksploracja: PERMIT `exploration.extra_draw` - `draw(extra=True)` dobiera 2 karty z tej samej talii,
    `POST /exploration/choose` wybiera jedną (reszta na stos odrzuconych); auto-dobór czeka na decyzję.
    „Po eksploracji planety” z kartą otwierającą produkcję (Freelancers) dopiero po tej produkcji
    (`ExplorationState.deferred_explored`, `exploration.after_grant` z `production`). Bot: `ExplorationChoose`.
  - `core/ship_roles` + FORBID `combat.space_ground_variant`: siły naziemne walczące jak statki z wartościami
    wariantu (Z-Grav tylko w trwającej walce kosmicznej w aktywnym systemie, Eidolon Maximum zawsze w
    przestrzeni); Assault Cannon i Demonstrate Your Power liczą je przez `space_ships`.
  - Rewersy kart (`combat.FLIP_SIDE_UNIT_IDS`) nigdy nie są wariantem bazowym; Eidolon Maximum wymaga
    `PlayerState.breakthrough_flipped` (`breakthrough.flip`/`flip_back`, `combat.player_variant`).
    Błąd danych AsyncTI4: `absol_naaz_mech_space` ma `source: pok` - wykluczony jawnie.
  - PERMIT `units.ground_moves_as_ship` (ruch/odwrót, pula floty, nie ładunek), FORBID
    `combat.ability_hit_immune` (Space Cannon, bombardowanie), FORBID `units.place_forbidden`
    (`unit_ops.place_units`, `board_reinforcements.can_place`), nowe zdarzenie `UNIT_REMOVED/AFTER`.
  - `strategic_action.begin_strategize_secondary(then=..., from_reinforcements=...)`: łańcuch okien secondary,
    żeton z rezerwy (bez `STRATEGY_TOKEN_SPENT`), pusta rezerwa = pula arkusza (`token_pool`).
  - Brother Milor Ω (Yin) za jednostkę statek+siła naziemna: wybór właściciela (F_yin 8, 8.1).
- UI: okno eksploracji („Draw 2 (Distant Suns)”, wybór 1 z 2 kart), okno secondary (koszt z rezerwy, wybór
  puli arkusza), chip przełomu „flipped” (`breakthrough.flipped` w web-data).
- Rulingi `F_naaz_rokha` z testami (`tests/factions/test_naaz.py`, scenariusze `test_flows_naaz.py`);
  domknięte odroczone: F_saar scavenge 2.2, F_yin milor Ω 8/8.1. Luki (`gap`): okno między flipem Eidolon a
  innymi zdolnościami startu walki (eidolon 2.1), Eidolon Maximum „albo pojemność” (eidolon-maximum 1),
  Direct Hit na Eidolon Maximum w walce naziemnej (6.1).
- ⚠️ Założenia do potwierdzenia: Garv and Gunn - planetę wybiera eksplorujący gracz (może zrezygnować);
  notatka AsyncTI4 „Eidolon Maximum na planecie walczy w walce kosmicznej” - NIE zaimplementowana (brak w tirules).

## 2026-11-19 — Entropic Scar (RULES.md 1.5), „Auto” żetonów w statusie, bez zaznaczania tekstu

- ✅ Anomalia Entropic Scar (Thunder's Edge, kafle `114` i `116` Lemox) - wcześniej flaga `isScar` w ogóle
  nie była czytana. `SystemDef.is_scar` -> anomalia `ENTROPIC_SCAR`; `core/entropic_scar.py` = jedno pytanie
  „czy blizna”. Blokady zdolności jednostek (przez i przeciw jednostkom w bliźnie): Sustain Damage
  (`battle.sustain_denied`), AFB (także nadany komponentem), Space Cannon (z blizny, w bliznę, Experimental
  Battlestation), Planetary Shield, Bombardment (inwazja i walka naziemna), Production jednostek, DEPLOY
  (Letani Behemoth, Dunlain Reaper, Scavenger Zeta, ZS Thunderbolt M2). Żeton Gamma w bliźnie wraca do puli.
- ✅ Start fazy statusu: statki w bliźnie -> oferta „may” (okno drzewa technologii, tryb GAIN, tylko
  nieposiadane technologie frakcyjne) za żeton z puli strategii; druga blizna = druga oferta. Nowe źródło
  hooków `SOURCE_RULE` (`rules_hooks.declare_rule_source`) - zasada ogólna posiadana przez każdego gracza.
- Rulingi `R_entropic_scars` z testami (`tests/rulings_general/test_rulings_entropic_scar.py`); zdjęte z długu.
- ⚠️ Założenia do potwierdzenia: DEPLOY nie stawia jednostki W bliźnie; Ion Storm to nie „wormhole token”.
- Przegląd anomalii: asteroidy, mgławica, supernowa, szczelina, blizna - obsłużone na kaflach. Żetony anomalii
  (`tokens/other.json`: nebula/asteroids/rift/entropicscar) nie mają dziś źródła w grze (włączone dodatki ich
  nie kładą) - silnik ich nie czyta.
- UI fazy statusu, krok 5: przycisk „Auto” (nowe żetony dopełniają pulę floty do największej floty, reszta do
  taktycznej; gracz zatwierdza). W grze sieciowej każdy widzi tylko SWOJĄ kartę rozdziału / punktowania,
  pozostali jako „Waiting for …” (`useCanActAs`).
- UI: globalnie wyłączone zaznaczanie tekstu i natywne przeciąganie obrazków (`ds/base.css`); pola edycji
  zostają zaznaczalne, wyjątek klasą `ds-selectable`.

## 2026-11-19 — Pole bitwy: bez ponownego wlotu po AFB i przeskoków po wrakach

- ✅ Szereg myśliwców liczony płasko (`wingRank` w `BattleFleet.tsx`): bez `div`-ów eskadr. Po stratach z AFB
  eskadry dzieliły się od nowa i myśliwce przechodziły do innego rodzica — React montował je od nowa (efekt
  „wlotu” i restart animacji). Szereg ma stały klucz = numer z `RANK` (wcześniej typ pierwszego okrętu).
- ✅ Domykanie szyku (FLIP) mierzy pozycje bez transformacji (`offset*`), działa też przy zmianie skali szyku
  i kontynuuje trwające dosuwanie (wcześniej po zniknięciu szeregu flota przeskakiwała).
- ✅ Fazy dryfu okrętów/silników/piechoty z id okrętu (`--ph`), dryf szeregu z numeru `RANK` — bez skoków
  po usunięciu wraku.
- Test: `frontend/src/domains/battle/battleFormation.test.ts`. Naprawiony błąd typów w
  `AgendaPassButtons.test.tsx` (blokował `tsc`).

## 2026-11-19 — Hesh and Prit (bohater Naaz-Rokha), kafelki kart strategii, mechy w kosmosie, kolejność reliktu

- ✅ Perfect Synthesis: jedno pole wyboru 0–2 kart strategii (`oi.multi`, kolejność kliknięć = kolejność
  rozstrzygania, F_naaz_rokha hesh 2–3) zamiast dwóch pól „First/Second” z opcją „None”; podpowiedź mówi
  o reliktcie i żetonach z rezerwy. Parametr `{"cards": [..]}`. Test okna w `tests/factions/test_naaz.py`.
- ✅ Kafelki kart strategii w oknach decyzji (Naaz, Hacan, Winnu, karty akcji): sama nazwa + „initiative N”,
  bez drobnego tekstu primary/secondary — ten jest pod ⓘ i w podpowiedzi (`DescribedOptionBody brief`).
- ✅ Walka w kosmosie: mechy (Z-Grav Eidolon) i piechota stoją prosto, bez obrotu okrętu (`BattleOverlay.module.css`).
- ✅ Scena odsłonięcia reliktu czeka na koniec sceny kluczowego momentu (`useHeroFx.stageBusy`, karencja
  1,2 s na feed) — najpierw animacja bohatera, potem relikt.

## 2026-11-19 — Paczka do rozesłania (PaxMagnifica.exe + zip) i samouczek w grze

- ✅ Paczka: `uv run python packaging/build_release.py` → `release/PaxMagnifica/` + `release/PaxMagnifica-<data>.zip`
  (~1,4 GB). Odbiorca rozpakowuje i klika `PaxMagnifica.exe` — bez Pythona, Node i dwóch okien.
  PyInstaller onedir (`packaging/pax_magnifica.spec`, cały pakiet `src` bo hooki frakcji są wykrywane `pkgutil`),
  obok `.exe`: `assets/` bez nieużywanych katalogów (`music_originals` 1,2 GB, `quick_reference`, `stickers`,
  `server_icons`), `docs/rules_tirules`, `frontend/dist`, `JAK_GRAC.txt`.
- ✅ `src/api/bundle.py` (`BundleApp`): jeden serwer na :8000 robi to, co w devie proxy Vite — `/bot/*` → API
  (z WebSocketem i lifespan), `/static` → assety, reszta → `dist` z fallbackiem SPA. USUWA `X-Forwarded-For`
  (bez proxy gość podałby `127.0.0.1` i udawał hosta, RULES.md 44.6); launcher uruchamia uvicorn z
  `proxy_headers=False`. Test: `tests/test_bundle.py` (prefiks, nagłówek, SPA, path traversal, WS, lifespan).
- ✅ `packaging/launcher.py`: `CUSTODIAN_ROOT` (nowe w `src/config.py`) = katalog `.exe`, `saves/` i
  `bug_reports/` obok `.exe`, pierwszy wolny port od 8000 (nie ubija cudzych procesów), adresy LAN w konsoli,
  `freeze_support` dla procesów roboczych bota. `src/api/__main__.py`: wydzielone `build_parser`/`build_server_app`.
- ✅ Samouczek (`frontend/src/domains/tutorial/`): okno „How to play” (13 rozdziałów: cel, ekran, runda, fazy,
  akcja taktyczna, walka, ekonomia, karty, gra sieciowa) — z toolbara mapy, z menu głównego i z panelu podpowiedzi.
  Panel „What now?” (lewy dół, nad czatem; zwija się do kompasu, przesuwany) mówi, co zrobić teraz: wybór karty,
  akcje tury, krok akcji taktycznej, walka, decyzja w oknie, cudza tura/bot, „Next phase” u mówcy, status, agenda.
  Logika: czysta `coachHint.ts` + testy; `HowToPlayModal.test.tsx`.
- E2E: lokatory `Play` z `exact: true` (nowy przycisk „How to play”). `tools.e2e.ts` „zoom mapy” pada też bez
  tych zmian — kursor testu (1300, 700) trafia w wachlarz kart strategii; do poprawy w teście.
- ✅ Zaproszenia w grze (okno Invites): link z adresem hosta w sieci zamiast `localhost`, ten sam port co strona
  (`network/inviteOrigin.ts` + test); przy kilku sieciach (dom + ZeroTier) wybór „Friends connect through”.
- `build_release.py`: nie nadpisuje `release/PaxMagnifica`, gdy gra z niego działa albo ma zapisy w `saves/`
  (PyInstaller czyści katalog razem z zapisami); `--out KATALOG` buduje obok.
