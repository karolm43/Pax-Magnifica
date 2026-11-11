# Plan: frakcje (H5 / E7) — bloki na sesje

Plan wdrożenia **wszystkich komponentów frakcyjnych**: zdolności, technologie frakcyjne, liderzy
(agent / commander / hero), przełom (Thunder's Edge), promissory notes frakcji oraz jednostki
frakcyjne (flagowiec, mech, jednostki specjalne). Rozwija sekcję „H5 — Frakcje" z
`PLAN_PELNA_ROZGRYWKA.md`. Stan: 2026-11-11.

> **Zasada nadrzędna bez zmian:** teksty i liczby WYŁĄCZNIE z assetów (`registry.catalog`,
> `catalog.faction_bundle(<id>)`), reguła w `docs/rules/R<NN>.md` ZANIM trafi do kodu, wyjątek =
> hook (nigdy `if faction == ...` w regule bazowej). Opisy mechanik poniżej są ORIENTACYJNE (do
> planowania) — rozstrzyga tekst karty z danych.

---

## 1. Punkt startowy (zweryfikowane w kodzie)

| Obszar | Stan | Co to znaczy dla frakcji |
|---|---|---|
| Rejestr hooków, źródła `SOURCE_FACTION/LEADER/BREAKTHROUGH/PROMISSORY` | ✅ | `owned_sources` już zwraca frakcję (id **i** rodzinę), odblokowanych liderów, odblokowany przełom, notki w strefie. Hooki można pisać od razu. |
| Silnik zdarzeń + oferty „may" (`on_event`, `PendingOffer`, `OffersModal`) | ✅ | Zdolności „When/After … you may" = ten sam wzorzec co technologie ogólne (RULES 56). |
| Akcja komponentu z dispatch (`component_action` → `register_effect`) | ✅ dla kart akcji, techów, reliktów, planet | Brak gałęzi dla **liderów, zdolności frakcji, przełomu, notek**. |
| Liderzy | ⚠️ tylko stan (`leader_states`, `exhaust_leader/ready_leader`, God-Mode) | **Brak** sprawdzania warunków odblokowania (`unlockCondition` w danych), zużycia (purge) bohatera, zagrania ACTION. |
| Promissory notes | ⚠️ ręka + `transfer` + strefa (`promissory_notes_in_play`) | **Brak** zagrywania z ręki, efektów, zwrotu do właściciela. 5 notek ogólnych (`_cf, _ps, _sftt, _ta, _an`) też bez efektów. |
| Przełom | ⚠️ `unlock_breakthrough`, `exhaust/ready_breakthrough` | Brak efektów (0/31). |
| Jednostki frakcyjne | ✅ statystyki z danych (`resolve_unit_variant`) | Pole `ability` (flagowce, mechy) bez hooków; raport pokrycia ich nie liczy. |
| Hooki frakcji | 1 (Arborec: doki nie produkują piechoty) | Pokrycie frakcji w `POKRYCIE_HOOKOW.md` §7: **0 / ~300**. |
| Mechaniki wspólne wielu frakcji | ❌ | **Przechwytywanie (capture)** — ~40 komponentów frakcyjnych; **koegzystencja (coexist)** — ~27; **żetony frakcyjne na mapie** (sleeper, breach, wormhole Creuss, galvanize); **sąsiedztwo zależne od gracza** (Creuss, Crimson, Empyrean). |

**Pułapka kluczy:** rodzina frakcji (`registry.faction_family` = `shortName`) różni się od id:
`ghost→creuss`, `jolnar→jol-nar`, `naaz→naaz-rokha`, `titans→ul`, `cabal→vuil'raith`,
`ralnel→ral nel`, `crimson→rebellion`, `keleres{a,m,x}→keleres`. Hook można zarejestrować pod id
(`ghost`) — `owned_sources` daje oba klucze — ale karty w danych (`faction: ...`) wskazują RODZINĘ.

---

## 2. Szablon jednego bloku frakcji (DoD)

Każdy blok frakcyjny przechodzi ten sam pipeline (wzór: `ARCHITEKTURA_KODU.md` §3a):

1. **Inwentarz** — `catalog.faction_bundle(<id>)` + jednostki frakcji; wypisać komponenty i ich okna
   (`OKNA_CZASOWE.md`, grep po id — nie czytać całości).
2. **Reguły** — podsekcja frakcji w `docs/rules/R62.md` (patrz §5): tekst z danych → interpretacja
   → źródło (tirules / LRR / rulingi) → ⚠️ ZAŁOŻENIA do potwierdzenia przez użytkownika.
3. **Kod** — moduł `src/core/hooks/factions/<id>.py` (jeden plik na frakcję, ~≤500 linii), każdy
   hook z `covers="<kategoria>:<id>"`; brakujący punkt zaczepienia → dodać w JEDNEJ funkcji
   centralnej (RULES 43.1a), nie w regule bazowej.
4. **Testy** — `tests/factions/test_<id>.py`, konwencja par (bez wyjątku / z wyjątkiem) + test
   kompletności frakcji (każdy komponent `IMPLEMENTED` albo jawnie `MANUAL` w `effects_status.json`).
5. **UI** — tylko to, czego nie pokrywają wspólne okna (oferty, formularz akcji komponentu, menu
   lidera). Nowe okno frakcyjne = wyjątek, uzasadniony w PROGRESS.
6. **QA + domknięcie** — pełne QA backend (+ front, gdy ruszany), odświeżenie
   `POKRYCIE_HOOKOW.md` i `OKNA_CZASOWE.md`, krótka sekcja w `PROGRESS.md`, commit.

**Rozmiar sesji:** ~10–12 komponentów i ≤2 nowe elementy UI. Frakcja „prosta" (modyfikatory,
mało okien) → dwie w sesji. Frakcja strukturalna (nowa mechanika planszy / talii) → jedna lub
dwie sesje.

---

## 3. Bloki (kolejność wykonania)

Legenda: **[F]** fundament, **[I]** wspólna mechanika, **[B]** blok frakcji. Liczba w nawiasie =
komponentów frakcji wg `POKRYCIE_HOOKOW.md` §7 (+ flagowiec/mech).

### Fala 0 — fundamenty (bez nich frakcje się nie domkną)

**F1 · Liderzy: cykl życia** (1 sesja) — `RULES 61.1`
- Warunki odblokowania commanderów i bohaterów: rejestr predykatów `register_unlock("leaders:<id>")`
  sprawdzany po zdarzeniach (kontrola planety, punktacja, badanie, walka…) → odblokowanie + wpis w
  logu. Bez predykatu = przycisk ręcznego odblokowania (MANUAL), żeby gra się nie blokowała.
- Agent: wyczerpanie przy użyciu; bohater: zużycie (purge, nowy stan `purged`).
- Dispatch w `component_action` dla liderów z „ACTION:" + oferty dla „When/After" (źródło już jest).
- Menu lidera w panelu gracza: „Użyj" (legalne tylko gdy można) zamiast samego God-Mode.
- Pilot: 1–2 liderów o prostym efekcie, żeby przetestować ścieżkę od końca do końca.

**F2 · Promissory notes: zagrywanie i zwrot** (1 sesja) — `RULES 61.2`
- Zagranie notki z ręki (przeciąganiem, jak karty akcji; podnieść można tylko legalną), zakaz
  zagrania własnej, umieszczenie w strefie odbiorcy, zwrot do właściciela wg warunku z tekstu.
- Notki reakcyjne w modelu STOP (ręka ukryta — jak karty akcji, RULES 43.4).
- 5 notek ogólnych jako wzorzec: Ceasefire, Political Secret, Support for the Throne,
  Trade Agreement, Alliance (Alliance = współdzielenie zdolności commandera → zależy od F1).

**F3 · Zdolności, przełomy, jednostki frakcyjne + rusztowanie** (1 sesja) — `RULES 61.3`
- Dispatch ACTION dla zdolności frakcji (`abilities:<id>`) i przełomu (`breakthroughs:<id>`).
- Źródło hooka dla jednostek frakcyjnych z polem `ability` (flagowiec/mech „na planszy"):
  klucz `units:<id>`, pomocnik „czy gracz ma tę jednostkę w systemie X".
- Raport pokrycia: dodać kategorię jednostek frakcyjnych; test kompletności per frakcja.
- Pakiet `src/core/hooks/factions/` (przeniesienie `factions_base.py` → `factions/arborec.py`),
  szablon `tests/factions/`, wskaźniki zdolności frakcji w panelu gracza (wzór `TECH_CONTEXTS`).

### Fala 1 — modyfikatory i proste okna (pilotaż pipeline'u)

| Blok | Frakcje | Zakres / nowe punkty zaczepienia |
|---|---|---|
| **B1** | Sardakk N'orr (8) + Barony of Letnev (9) | Modyfikatory rzutów walki, przerzut za TG na start rundy, limit floty (punkt `fleet_pool.capacity`). Najlepszy pilot: mało UI. |
| **B2** | Universities of Jol-Nar (10) | −1 do rzutów, Technology secondary jako primary, pomijanie wymagania przy badaniu (punkt w `technology`). |
| **B3** | Federation of Sol (9) + Arborec (8, dokończenie) | ACTION za żeton strategii (wystawianie piechoty), +1 żeton w statusie, Mitosis na start statusu. |
| **B4** | Emirates of Hacan (10) + Winnu (9) | Transakcje (RULES 47): bez sąsiedztwa, karty akcji w transakcji, Trade secondary bez żetonu; Mecatol/Custodians bez kosztu, struktury po zdobyciu Mecatolu. |

### Fala 2 — zdolności z oknami reakcji / decyzjami

| Blok | Frakcje | Zakres |
|---|---|---|
| **B5** | Mentak Coalition (9) | Ambush (rzut przed walką), Pillage (reakcja na TG/transakcję sąsiada). |
| **B6** | Xxcha Kingdom (10) | Peace Accords (po Diplomacy), Quash (podmiana agendy) — dotyka `agenda_phase`. |
| **B7** | Yin Brotherhood (9) | Indoctrination (start walki naziemnej, płatność wpływem), Devotion (poświęcenie statku = trafienie). |
| **B8** | Argent Flight (9) | Zeal (głosy + głosowanie pierwsze), Raid Formation (nadwyżka AFB). |
| **B9** | L1Z1X Mindnet (9) | Assimilate (podmiana struktur przy przejęciu), Harrow (bombardowanie po rundzie walki naziemnej). |
| **B10** | Embers of Muaat (9) | Star Forge (ACTION), ruch przez supernowe, bohater zmieniający planszę. |
| **B11** | Clan of Saar (9) + Naaz-Rokha (9) | Ruchome doki, punktacja bez kontroli domu, +1 TG po przejęciu; dodatkowa karta eksploracji, fragmenty → relikt/żeton, mech w przestrzeni. |
| **B12** | Naalu Collective (10) | Żeton „0" (kolejność inicjatywy — `turn_flow`), Foresight (ucieczka żetonem strategii). |

### Fala 3 — wspólne mechaniki + frakcje strukturalne

| Blok | Zakres |
|---|---|
| **I1 · Przechwytywanie (capture)** | Strefa przechwyconych jednostek gracza (stan, zwrot, limity, widok w panelu), reguła z tirules (`R_capture`) — wspólna dla ~40 komponentów. |
| **B13** | Vuil'Raith Cabal (10): Devour, Amalgamation, Riftmeld, dok-szczelina grawitacyjna, bohater. |
| **I2 · Żetony frakcyjne na mapie** | Warstwa żetonów w systemie/na planecie (sleeper, breach, wormhole Creuss, galvanize pod jednostką), render + God-Mode. |
| **B14** | Titans of Ul (10): Terragenesis, Awaken, Coalescence, notka Terraform. |
| **I3 · Sąsiedztwo zależne od gracza** | Punkt `adjacency.extra_for_player` w grafie planszy (sąsiedztwo ≠ przejezdność — osobna warstwa). |
| **B15** | Ghosts of Creuss (10): Quantum Entanglement, Slipstream, Creuss Gate, żetony wormhole (I2+I3). |
| **B16** | Empyrean (11): Voidborn, Aetherpassage, Dark Whispers (2 notki). |
| **B17** | Nekro Virus (12): Valefar Assimilator, Technological Singularity, Galactic Threat (przewidywanie agendy), Propagation (żetony zamiast badań). |
| **B18** | Nomad (11): 3 agentów (The Company), ulepszenie flagowca, Future Sight. |
| **B19** | Yssaril Tribes (10): Stall Tactics, Scheming, Crafty; agent kopiujący cudzych agentów → **po wszystkich agentach**. |
| **B20** | Mahact Gene-Sorcerers (10): Edict (cudze żetony w puli floty), Imperia (cudzy commanderzy → **po F1 i większości frakcji**), Hubris. |
| **B21** | Council Keleres (16, 3 warianty): The Tribuni (setup po innych, przejęcie domu), Council Patronage, Law's Order (ignorowanie praw → **wymaga efektów agend**), 3 bohaterów. Możliwe 2 sesje. |

### Fala 4 — Thunder's Edge

| Blok | Zakres |
|---|---|
| **I4 · Koegzystencja (coexist)** | Wspólne jednostki na planecie bez walki, wpływ na kontrolę/produkcję/cele — ~27 komponentów. |
| **B22** | Deepwrought Scholarate (9): Research Team, Oceanbound (karty oceanów) + dług setupu: 2 technologie startowe z pustą listą opcji (RULES 16). |
| **B23** | Last Bastion (11): Liberate, Galvanize (żetony z I2), Phoenix Standard. |
| **B24** | Crimson Rebellion (13): Sundered, Incursion (breach, I2+I3), Sorrow (kafel domowy). |
| **B25** | Ral Nel Consortium (9): Survival Instinct (reakcja ruchem), Miniaturization (struktury w przestrzeni). |
| **B26–B27** | Firmament → Obsidian (9 + flip): plot cards (punktowanie cudzych sekretów), Puppets of the Blade, przejście na Obsidian (The Blade's Orchestra, odwrócenie komponentów). 2 sesje. |

**Razem:** 3 fundamenty + 4 wspólne mechaniki + 27 bloków frakcyjnych ≈ **34 sesje**.

---

## 4. Zależności i ryzyka

- **Efekty agend (0/123)** są w `PROGRESS.md` przed frakcjami. Twarda zależność ma tylko Keleres
  (Law's Order); Xxcha/Argent/Nekro potrzebują jedynie fazy agendy (✅). Fale 0–2 mogą iść równolegle
  z agendami.
- **Agenci/commanderzy innych frakcji** (Yssaril, Mahact, notka Alliance): zrobić te frakcje na końcu,
  gdy większość liderów działa.
- **Hooki at_start/at_end/during** (16 zdarzeń nieemitowanych): dopiąć emisję zdarzenia w bloku,
  który pierwszy go potrzebuje (test `test_emitted_by_zgadza_sie_z_kodem`).
- **Bot (etap 3):** każdy hook z decyzją musi mieć `inputs` (formularz) — bot dostanie te same
  wybory co człowiek. Bez ukrytych automatów (RULES 56).
- **Ryzyko rozmiaru:** frakcje z bohaterem przebudowującym planszę (Muaat, Creuss, Titans) — bohater
  może trafić do osobnej mini-sesji, reszta frakcji nie czeka.

---

## 5. Numeracja reguł

- `docs/rules/R61.md` — fundamenty frakcji: 61.1 liderzy, 61.2 promissory notes, 61.3 zdolności /
  przełomy / jednostki frakcyjne, 61.4+ wspólne mechaniki (capture, żetony, sąsiedztwo, coexist).
- `docs/rules/R62.md` — frakcje: jedna podsekcja na frakcję w kolejności realizacji (62.1 Sardakk,
  62.2 Letnev, …). Jeśli plik przekroczy ~400 linii — dzielić na `R63.md` (Fala 3) i `R64.md` (TE).

## 6. Status bloków

| Blok | Status |
|---|---|
| F1 Liderzy | ⬜ |
| F2 Promissory notes | ⬜ |
| F3 Zdolności / przełomy / jednostki | ⬜ |
| B1–B12 (Fale 1–2) | ⬜ |
| I1–I3, B13–B21 (Fala 3) | ⬜ |
| I4, B22–B27 (Fala 4) | ⬜ |
