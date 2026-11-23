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

## 2026-11-19 — Podział dużych plików (mniej tokenów na odczyt)

- Backend (warstwy tylko w dół; moduł bazowy eksportuje nazwy dalej `n as n`, wywołania `battle.x` bez zmian):
  `battle.py` 2134 → 1593 + `battle_units.py` (jednostki, trafienia, Sustain) + `battle_rerolls.py`
  (przerzuty/zmiany kości po rzucie: relikty, Fire Team, War Funding); `invasion.py` 1536 → 779 +
  `invasion_common.py` / `invasion_bombard.py` / `invasion_defense.py`; `movement.py` 1426 → 987 +
  `movement_paths.py`; `web_data.py` 1922 → 297 + `web_game` / `web_tiles` / `web_player_units` /
  `web_players`; `schemas.py` 1833 → pakiet `api/schemas/` (`common`, `setup`, `tactical`, `combat`, `cards`).
- Front: `useBoardEditor.ts` 1853 → 1180 + `api/boardQueries.ts` (zapytania tylko do odczytu, `export *`);
  `BattleOverlay.tsx` 1509 → 763 + `BattleVolley.tsx` + `BattleAssaultCannon.tsx`.
- Pominięte: `GameStatePanel.tsx` (równoległa sesja ma w nim niezacommitowane zmiany), rdzeń maszyny stanów
  `battle.py` i jeden hook `useBoardEditor` (wzajemna rekurencja / jeden hook — podział zmieniłby API).
- Testy: `monkeypatch` kości przerzutu celuje teraz w `battle_rerolls`. Opis warstw: `ARCHITEKTURA_KODU.md`.
- QA: pytest (pełny) ✓, ruff ✓, mypy ✓, tsc ✓, eslint ✓, vitest (battle, api, game-shell) ✓, build ✓.
  e2e pominięte. Wymaga restartu backendu (nowe moduły).

## 2026-11-19 — Porządek ekranu gry (mniej okien, nic się nie nakłada)

- Setup: „Skip setup (random)” widoczny TYLKO z opcją Settings → „Skip phases button (God-Mode)”
  (`GameSetupOverlay.tsx`); e2e włączają ją przez `enableSkipShortcuts` (`e2e/fixtures.ts`) + nowy test „bez opcji brak przycisku”.
- Panel fazy (`GameStatePanel`, wariant info): bez listy kart strategii i bez kolejności wyboru w fazie strategii
  (pokazuje to stół kart); martwa gałąź info w `StrategyCardPicker` usunięta.
- „What now?” = sekcja panelu fazy (`tutorial/CoachSection.tsx`, dawniej osobne okno `CoachPanel` w lewym dole,
  nachodziło na panel fazy i czat); zwija się nagłówkiem do jednej linii.
- Czat przypięty do lewego dolnego rogu (`bottom: 16px`, nie `--hand-dock-clear` — rozwinięta ręka wypychała go
  pod panel fazy); dok akcji taktycznej i panel fazy kończą się nad ikoną czatu.
- Invites hosta: przycisk w nagłówku (`InvitesButton` w `HeaderGameControls`) zamiast pływającego na planszy.
- Stół kart strategii: bez wiersza „Now picking / Speaker” (chipy kolejki: „picking…”, korona mówcy); baner mieści
  się między panelem fazy a centrum decyzji.
- Ręka: pusta zakładka kurczy się do linii komunikatu (zamiast 176 px pustej tacy).
- QA: tsc ✓ (poza niezacommitowanym `useBoardEditor.ts` równoległej sesji), eslint ✓, vitest (game-shell, tutorial,
  network, setup, chat) ✓, build ✓, e2e 8/8 (tools.e2e: zoom zwija stół kart przed kółkiem). Backend bez zmian.

## 2026-11-22 — B12: The Naalu Collective (RULES.md 62.16)

- ✅ `core/hooks/factions/naalu.py`: Telepathic, Foresight, Gift of Prescience, Neuroglaive, Hybrid Crystal
  Fighter II, Matriarch, Iconoclast TE, Z'eu (TE), M'aban (Codex), The Oracle, Mindsieve. Starsze warianty
  (Z'eu/Z'eu Ω, M'aban PoK, Iconoclast/Iconoclast Ω) = `na` w `rulings_status.json`.
- Rdzeń (punkty ogólne, bez nazw frakcji):
  - Żeton „0”: `core/initiative_zero.py` (efekt gracza, inicjatywa 0 w `turn_flow.turn_order` /
    `strict_initiative_order`, zdejmowany przy zwrocie kart strategii w `status_phase.finish_status`); okno reakcji
    „koniec fazy strategii” (`reactions_misc.strategy_phase_end`) dla notek z ręki.
  - `command_tokens.place_token` = jedyne położenie żetonu w systemie + nowe zdarzenie `COMMAND_TOKEN_PLACED/AFTER`
    (aktywacja, odwrót, Diplomacy, Signal Jamming, Stymie...).
  - Pula floty: PERMIT `fleet_pool.fighters_overflow` + MODIFY `fleet_pool.fighters_per_ship` (HCF II = 1/2 statku,
    w górę); `FleetReport.excess_after`, usuwanie nadwyżki bez zbędnych jednostek.
  - Inwazja: FORBID `invasion.ground_force_types` (`ship_roles.ground_force_types`) — myśliwce Matriarch lądują,
    walczą, obrywają w Space Cannon Defense, wracają do przestrzeni po walce i przed Establish Control
    (`invasion.return_ships_to_space`); widok inwazji w API pokazuje je jako siły do lądowania.
  - `core/peek.py` + FORBID `info.peek`: stały podgląd (M'aban) w web-data `gameState.peek`; talia agend zasiewana
    przy odblokowaniu M'aban.
  - `combat.resolve_unit_variant` i `web_player_units`: przy remisie rangi wygrywa wariant z `faction.units`
    (wcześniej kolejność rejestru dawała Iconoclast PoK zamiast TE).
  - Dacxive Animators: tylko z ocalałą siłą naziemną na planecie (F_naalu matriarch 3).
- UI: znacznik żetonu „0” na płytce karty strategii (`StrategyCard zeroToken`, `gameState.initiativeZero`), podgląd
  M'aban w liniach podglądu ręki (`BottomHandDock`), efekt bohatera The Oracle (`heroBoardFx.ts`). Oferty
  (Foresight, Z'eu, The Oracle, Iconoclast) i Mindsieve (Available now) idą przez wspólne okna.
- Rulingi `F_naalu` z testami (`tests/factions/test_naalu.py`, scenariusze `test_flows_naalu.py`); F_muaat umbat 4/4.1
  → `na` (aktywny M'aban nie produkuje). Luka: Neuroglaive przy Mahact (`requires faction:mahact`).
- ⚠️ Założenia do potwierdzenia: Foresight zabiera siły naziemne z przestrzeni automatycznie (mechy, potem piechota,
  do pojemności); Gift of Prescience gra się w oknie po komplecie kart strategii, zanim mówca kliknie „Next phase”.

## 2026-11-22 — Naalu: wybór + „Auto” w Foresight, pauza końca fazy strategii

- Decyzja użytkownika: każdy wybór gracza = wybór ręczny + „Auto” (także `CLAUDE.md`). Ogólnie:
  `oi.number(..., auto=N)` — UI wstawia wartość Auto i pokazuje przycisk „Auto” (`DecisionField`), pominięte pole
  = Auto (`validate_params`, `single_params`, bot).
- Foresight: gracz wybiera, ile mechów i piechoty z przestrzeni zabrać (pola `carry_mech` / `carry_infantry`,
  Auto = do pojemności, najpierw mechy — ⚠️ ZAŁOŻENIE); ponad pojemność = 422, niezabrane zostają.
- Pauza ochronna (54.10) w oknie „koniec fazy strategii”: `PAUSE_POINTS` (`PHASE/END`), uprawnieni = gracze z notką
  w ręce poza właścicielem notki frakcji reagującej w oknie (`promissory_play.faction_note_owners`, jawne);
  `turn_flow.next_phase` z fazy strategii czeka na koniec pauzy.
- Poprawka: oferty z położenia żetonu w trakcie primary (Diplomacy + Z'eu) nie otwierają własnego okna — czekają
  w oknie secondary (fuzz seed 11 stał).
- QA: pytest (factions, engine, reaction pause, strategia) ✓, ruff/mypy ✓, tsc ✓, eslint ✓, vitest (offers, api) ✓.
  Pełnego pytest nie puszczałem na tym drzewie: równoległa sesja ma niezacommitowane zmiany (Vuil'raith,
  `transaction.py` — czerwony `test_pride_of_kenara_w_gravity_rift_rzut` to jej zmiana). Build/e2e pominięte
  (bez nowych modułów frontu).

## 2026-11-22 — I1 Przechwytywanie (capture) + B13 The Vuil'raith Cabal (RULES.md 61.5, 62.17)

- **I1 capture** (`core/capture.py`, punkt centralny): `PlayerState.captured_units` (statki/mechy wg pierwotnego
  właściciela, także własne) i `captured_tokens` (żetony myśliwców/piechoty z puli). Rezerwa właściciela bez
  przechwyconych (`production.reinforcements_left`), zniszczenie → hook PERMIT `capture.destroyed`
  (`unit_ops.remove_units`), z rezerwy / z planszy bez zniszczenia, zwrot (pudełko po eliminacji), blokada doku
  oddaje statki od razu (`step_settle` → `capture.release_blockaded`), zakaz przechwytywania od blokującego,
  transakcja zwraca statki/mechy tylko właścicielowi (`TransactionSide.captured_units`). Widok: `nombox`
  w web-data (komponent `Nombox`, teraz z pełną nazwą frakcji). Feed: `ability_notes` „captured …”.
- **Anomalie z jednostek** (`core/map_anomalies.py`, `HexGrid.sync_extra_anomalies`): Dimensional Tear czyni system
  gravity rift dla wszystkich; własne statki Cabal nie rzucają (`movement.rift_roll_nodes`, `rolls_at`).
  Pojemność „Up to N fighters” z tekstu zdolności doku (dane bez `capacityValue`).
- **Cabal** (`hooks/factions/cabal.py`): Devour, The Terror Between (także po zniszczeniu w tej rundzie),
  Reanimator, Amalgamation (pole produkcji `captured`, chipy w `ProductionOverlay`), Riftmeld (skip
  `captured:<właściciel>`, sekcja w `TechnologyOverlay`), Vortex, The Stillness of Stars (oferta po uzupełnieniu
  commodities; zamiana bez „gain”), That Which Molds Flesh (2 myśliwce/piechota poza limitem, unlock 3 szczeliny),
  Dimensional Anchor (rzut raz na statek, nadwyżka ładunku przez okno CAPACITY też przechwycona), Crucible
  (bez rzutów, jedno dodatkowe +1, także z Nav Suite), Al'raith Ix Ianovar (Fracture bez rzutu, przesunięcie
  2 ingressów do szczelin — Available now, +1 ruchu z The Fracture).
- Poprawka: oferty „after replenishes” w trakcie primary Trade czekają w oknie secondary
  (`economy.replenish_commodities(open_window=False)`) — wcześniej blokowały otwarcie okna secondary.
- Rulingi: `F_vuilraith` + `R_capture` (usunięty z długu, limit 211) z testami (`tests/test_capture.py`,
  `tests/factions/test_cabal.py`, scenariusze `test_flows_cabal.py`). Statusy: Amalgamation 5 i Stillness 4 (`gap`),
  Anchor 5 / R_capture notes 4 (`requires` Nekro/Yssaril).
- ⚠️ Do decyzji użytkownika: Trade primary zbiera wybór graczy z darmowym secondary PRZED primary, więc agent wybiera
  już po nim (ruling Stillness 4); okno przesunięcia ingressów trwa do końca tury, w której przełom wszedł do gry.
- Stół transakcji: sekcja „Captured units” (stepper na typ, sylwetka w barwie partnera, tylko statki/mechy
  partnera z Nombox, tylko gdy wolno kłaść komponenty), podsumowanie „Returns captured …”; scenariusz API
  `test_transakcja_zwraca_przechwycony_statek`. Przy okazji: brak `hint` w `DecisionFields.test.tsx` (tsc).

## 2026-11-23 — Cabal: przesunięcie ingressów zaraz po wejściu Fracture

- Decyzja użytkownika: Al'raith Ix Ianovar przesuwa ingressy od razu po rozłożeniu ich wg zasad, nie
  w oknie „Available now” do końca tury. Nowe zdarzenie `GameEvent.FRACTURE_INGRESS_PLACED`
  (`fracture.announce_ingress_placed`: po `_enter` bez wyborów i po ostatnim `choose_ingress`); hook
  Cabal = oferta (`ingress_offer`). Fracture już w grze → oferta od razu po wejściu przełomu.
- QA: pytest (Cabal, Fracture/ekspedycje, zdarzenia, triggery) ✓, ruff/mypy ✓.

## 2026-11-23 — Frakcja The Titans of Ul (B14, RULES.md 62.18) + żetony frakcyjne na mapie (I2, 61.6)

- **Żetony frakcji** (`core/faction_tokens.py`, `SystemState.faction_tokens = {strefa: {rodzaj: właściciel}}`):
  sleeper ×5 (AsyncTI4), place / move / remove, zwrot przy wymianie kafla (Nova Seed) i zniszczeniu planety.
  Widok: żeton `sleeper` na planecie w web-data, `sleeperTokensReinf` w panelu gracza, feed
  `faction_token` / `faction_token_removed`.
- **Titans** (`hooks/factions/titans.py`): Terragenesis (oferta po eksploracji: pula albo przeniesienie – klik
  planety), Awaken (migawka żetonów i PDS na `SYSTEM_ACTIVATED/WHEN`; per żeton PDS / mech+piechota / zostaw; PDS
  z planszy przy pustej rezerwie; cudza planeta bez sił naziemnych przejęta od razu, z siłami – walka w Invasion),
  Coalescence (reguła bazowa), Hel-Titan jako struktura i siła naziemna (FORBID `units.structure_ground_forces`:
  obrońcy, sporne planety, utrzymanie po walce, cel bombardowania bez tarczy; bez trafień SCD), Ouranos (DEPLOY
  z migawki), Hecatoncheires („mech zamiast PDS” w `place_structure` – Construction i Awaken), Tellurian
  (użycie w oknie: anuluje 1 trafienie walki / Space Cannon / bombardowania dowolnego gracza), Tungstantus
  (unlock 5 struktur; przełącznik w `ProductionOverlay`, TG przed zapłatą), Geoform (attachment `titanshero`:
  +3/+3, SPACE CANNON 5×3 dla kontrolera Elysium; karta przy planecie blokuje ponowne użycie), Terraform
  (attachment `titanspn` +1/+1 i 3 cechy – `planet_stats.traits`, `exploration.planet_traits(state=…)`, cele;
  notka nie wraca i nie leży w strefie), Slumberstate zdanie 3 (prośba → decyzja kontrolera Allow/Refuse).
- Zmiany wspólne: karty strategii (Construction, Warfare) produkują tylko dokami (`ProductionGrant.producer_types`,
  F_ul hel-titan 1); `invasion.cancel_bombardment_hits`; SPACE CANNON z attachmentów (`space_cannon`);
  attachmenty z notek i liderów (`planet_stats._card_attachment`); efekt bohatera na planszy `titanshero`.
- Rulingi `F_ul` (mapa `titans → F_ul`) z testami (`test_titans.py`, scenariusze `test_flows_titans.py`); Farran
  + Hel-Titan (F_letnev 2.1) ma test. Statusy `gap`: przełom zdania 1–2 (koegzystencja, blok I4), Hel-Titan 3
  (Decoy Operation / Transit Diodes).
- ⚠️ ZAŁOŻENIA (do potwierdzenia): Awaken – każdy żeton osobno, „Auto” = PDS; Tungstantus – „Auto” = włączone;
  Slumberstate – prośba w dowolnej chwili fazy akcji, bez akcji; Tellurian nie anuluje AFB (brak kroku przypisania).


## Efekty bohaterów na planszy — przegląd i nowe znaczniki frakcji (RULES.md 64.4)

- Ul the Progenitor (Titans) nie miał sceny ani efektu: Geoform nie purge'uje karty (dołącza ją do Elysium),
  więc feed nie miał faktu `leader purged`. `momentsForEntry` rozpoznaje teraz fakt `attached` z kartą bohatera
  (sprawca = `actor_id`, planeta w `planets`); cel efektu `planet` = system Elysium. Test backendu w
  `tests/test_activity.py`, testy frontu w `keyMoments.test.ts`.
- Cabal (Dimensional Anchor): wir startuje z systemów z dokami Cabal (Dimensional Tear, cel `docks`), macki sięgają
  do SĄSIEDNICH systemów (`neighborTiles` — siatka heksów, tylko wizualizacja) i wciągają ich okręty.
- Każdy bohater ma własny znacznik (`layers/HeroFxMarks.tsx` + `.module.css`): Letnev celowniki, Jol-Nar obwody,
  Mentak haki abordażowe, Argent podwójna spirala, Yin kapsuły z klonami, L1Z1X siatka materializacji + zakłócenia,
  Saar fala Armageddon Relay z doków, Naalu oko psioniczne + mgła, Titans szczeliny magmy / rdzeń tytana w płytach /
  3× SPACE CANNON, Cabal Event Horizon. Arborec dostał zarodniki, Sol rdzeń słupa, Xxcha siatkę tarczy.
- Nowe w przepisie: `quake` (wstrząs planszy przez `translate` kontenera kafli — nie psuje zoomu; wyłączone przy
  prefers-reduced-motion), przejścia `static` i `mist`, dźwięki dla wszystkich bohaterów.
- QA: vitest (KeyMoments, map), tsc app, eslint, pytest `test_activity`; zrzuty animacji (puppeteer) obejrzane.

## Efekty bohaterów: miejsce działania z feedu (fakty `area`, RULES.md 64.4)

- Przegląd wszystkich 18 bohaterów (Arborec … Titans): efekty z ACTION celowały zbyt szeroko (np. Sol świecił
  nad wszystkimi systemami z jednostkami). `core/activity.py` dopisuje we wpisie z użyciem bohatera (purge albo
  dołączenie karty) fakty `area` (pozycja + `gain`/`loss` jednostek gracza albo `token_removed`); feed ich nie
  wypisuje (`describeActivity`), `momentsForEntry` przenosi je do momentu (`areas`, `self` = bohater).
- Przepis może mieć `area` (zapasem zostaje `target`): Sol — systemy, z których zniknęły jego żetony (słup światła
  unosi żeton); Saar — system, gdzie rywale stracili jednostki; Argent / L1Z1X — systemy docelowe floty;
  Yin / Xxcha / Arborec — systemy z nowymi jednostkami. Bez wpływu na planszę (Jol-Nar, Naaz, Naalu, Winnu) bez
  zmian; reakcje (Hacan, Mentak, Sardakk, Muaat) — aktywny system / Nova Seed.
- Testy: `tests/test_activity.py` (fakty `area`), `tests/factions/test_hero_area_feed.py` (Sol/Saar/L1Z1X przez
  API), vitest `keyMoments`/`heroBoardFx`; zrzut efektu Sol obejrzany.

## 2026-11-23 — AFB przez krok przypisania (Shields Holding, Tellurian) + „Auto” w wyborach z listy

- Decyzja użytkownika: trafienia zwykłego AFB przypisuje właściciel myśliwców w kroku ASSIGN (jak Waylay;
  `afb_assign`, wymagany cel `hit_targets` = myśliwce, wybór + „Auto”), więc przed przypisaniem anulują je
  Shields Holding (C_action_cards 4.1) i Tellurian (RULES.md 39 W4, 53, 62.18).
- Shields Holding: audyt rulingów C_action_cards (1–5, 4.1) z testami, karta zdjęta z długu (limit 210).
  Naprawiony błąd: drugą Shields Holding gracz mógł zagrać na ten sam rzut (ślad w `combat.effects`).
- `oi.choice(auto=...)`: przycisk „Auto” w wyborach z listy (`DecisionFields`), pominięte pole = opcja Auto.
  Titans: Awaken = PDS, źródło żetonu = pula, Tellurian = trafienie we własne jednostki, Ouranos = pierwszy PDS,
  Terraform = planeta o najwyższej sumie wartości, Slumberstate: kontroler „Auto” = odmowa.
- QA: pytest całość ✓, ruff/mypy ✓, tsc/eslint/vitest (offers, ActivityPanel) ✓, e2e 8/8 ✓.

