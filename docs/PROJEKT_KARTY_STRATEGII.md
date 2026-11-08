# Projekt: zagranie kart strategii (primary + secondary, sieć-ready)

Status: PROJEKT do akceptacji (nie zaimplementowany poza walidacją „jedna akcja na turę",
patrz RULES.md 30.3). Źródła reguł: `docs/rules_tirules/R_strategic_action.md`,
`R_strategy_card.md`, `R_leadership|diplomacy|politics|construction|trade|warfare|technology_sc|imperial.md`,
`R_action_phase.md`. Teksty kart: `assets/data/strategy_cards/pok.json` (+ `te.json`).

## 1. Dlaczego obecny szkielet nie wystarczy

`core/strategic_action.py` robi dziś: efekt primary w JEDNYM wywołaniu → okno
`STRATEGY_SECONDARY` → respondent „wykonaj/pas" bez żadnych danych. To działa tylko dla
Leadership (+3 żetony). Prawie każda karta wymaga WYBORÓW gracza (system, planeta, technologia,
cel, pula żetonów, gracze), a secondary wymaga KOSZTU (żeton ze strategy pool, wpływ, zasoby).
Dodatkowo:

- secondary NIE pobiera dziś żetonu ze strategy pool (reguła: 1 żeton, wyjątek Leadership;
  w Trade gracze wskazani przez aktywnego robią secondary za darmo i MUSZĄ),
- gracz bez żetonu w strategy pool nie może „follow" (poza Leadership),
- spasowany gracz MOŻE robić secondary (R_action_phase) — okno nie może go pomijać.

## 2. Model: rozstrzyganie wieloetapowe zamiast jednego strzału

Nowy stan w `GameState`: `pending_strategy` (jedna aktywna akcja strategiczna naraz):

```
StrategyResolution:
  initiative: int            # która karta
  owner_id: str              # aktywny gracz
  stage: PRIMARY | SECONDARY | DONE
  step: str                  # np. "choose_system", "ready_planets", "pay"
  draft: dict                # wybory zebrane do tej pory (walidowane, jeszcze nie zatwierdzone)
```

- PRIMARY: krok po kroku, tylko `owner_id` może wysyłać odpowiedzi. Efekt stosowany
  atomowo na końcu kroku (draft → state), żeby błędny klik nie zostawiał stanu w połowie.
- SECONDARY: nadal `TimingWindow(STRATEGY_SECONDARY)`, ale odpowiedź respondenta to
  `{decision: follow|pass, payload: {...}}`, a „follow" przechodzi w mini-kroki karty
  (np. wybór technologii + płatność) na tym samym oknie (cursor stoi, dopóki respondent
  nie zakończy kroków). Kolejność: od gracza po lewej aktywnego, zegarowo (już jest).
- Wyczerpanie karty: po zamknięciu okna secondary (reguła R_strategic_action). Dziś
  wyczerpujemy przy zagraniu — zachować jako flagę „played", a `exhausted` ustawiać po oknie.
- Każda karta = moduł `core/strategy_cards/<karta>.py` z funkcjami
  `primary_steps()`, `apply_primary(step, draft)`, `secondary_cost()`, `apply_secondary(...)`.
  Dispatch jak dziś po inicjatywie. Asymetria frakcji/tech (np. Fleet Logistics: 2 akcje na
  turę) jako hooki `rules_hooks` (E7), nie `if faction`.

## 3. Sieć: co z tego wynika

- Serwer jest autorytetem; każda odpowiedź niesie `player_id` i jest sprawdzana względem
  `owner_id` (primary) albo `current_responder` (secondary). Nikt nie odpowiada za kogoś innego.
- Okno secondary jest SEKWENCYJNE (jeden respondent naraz) — zgodnie z regułą i najprostsze
  w sieci: broadcast „teraz decyduje X", reszta widzi tylko, kto już zdecydował i jak
  (follow/pass), bez szczegółów prywatnych.
- Informacja ukryta: Politics (podgląd 2 kart agendy) i dobrane karty akcji/tajne cele idą
  WYŁĄCZNIE do właściciela (`core/visibility.py`); publicznie tylko „X obejrzał agendę".
- Timeout/rozłączenie: pole `deadline` w oknie i polityka „auto-pass" (bot/administrator) —
  do ustalenia przy module sieciowym; teraz hot-seat, więc brak.
- Bot: te same funkcje `core/`, bot odpowiada przez ten sam kontrakt (`decision` + `payload`).
- Idempotencja: każda odpowiedź niesie `step` i `window_id`/`version`; stara odpowiedź
  (opóźniona w sieci) jest odrzucana 422/409 zamiast zastosowana dwa razy.

## 4. Analiza kart (PoK; TE ma inne Construction i Warfare — patrz uwagi)

Legenda UI: 0 = wystarczy przycisk/potwierdzenie, S = mały selektor, M = wybór na mapie,
P = płatność (wpływ/zasoby z planet), H = duży dedykowany widok.

| # | Karta | Primary (wybory) | Secondary (koszt + wybory) | UI |
|---|-------|------------------|----------------------------|----|
| 1 | Leadership | +3 żetony (wybór puli) → opcjonalnie wydaj wpływ: 1 żeton / 3 wpływu | Wydaj wpływ → żetony; BEZ żetonu strategii | P + S (pula) |
| 2 | Diplomacy | Wybierz system (nie Mecatol) z własną planetą → inni kładą żeton → odnów 2 planety | 1 żeton strategii → odnów do 2 planet | M + S (planety) |
| 3 | Politics | Wybierz nowego mówcę (nie obecny) → +2 karty akcji → podgląd 2 kart agendy, góra/dół, kolejność | 1 żeton strategii → +2 karty akcji | S (gracz) + H-mały (agenda, prywatny) |
| 4 | Construction | 1 PDS lub dok na planecie + 1 PDS (bez wymogu żetonu w systemie) | 1 żeton: połóż w dowolnym systemie (jeśli już jest — wraca do rezerwy) + 1 PDS lub dok na planecie w tym systemie | M + S (planeta/struktura) |
| 5 | Trade | +3 TG, uzupełnij commodities, wskaż graczy, którzy robią secondary za darmo | 1 żeton → uzupełnij commodities (lub za darmo, gdy wskazany) | S (multi-select graczy), reszta 0 |
| 6 | Warfare | Zdejmij 1 swój żeton z planszy → do wybranej puli → opcjonalnie redystrybucja | 1 żeton → PRODUCTION jednego doku w home system (żeton nie ląduje w systemie) | M + redystrybucja (jest w statusie) + Production |
| 7 | Technology | Zbadaj 1 technologię + opcjonalnie 2. za 6 zasobów | 1 żeton + 4 zasoby → 1 technologia | **H (drzewo technologii)** + P |
| 8 | Imperial | Zdobądź 1 cel publiczny (jeśli spełniasz) → kontrola Mecatol: +1 VP, inaczej tajny cel | 1 żeton → dobierz tajny cel | S (wybór celu) + S (limit 3 tajnych → zwrot) |

Wnioski o prostocie: „primary jest proste" zachodzi naprawdę tylko dla Trade. Pozostałe
primary też wymagają wyborów, więc primary musi być krokowe (sekcja 2), nie jednym POST-em.

### Uwagi do poszczególnych kart

- **Leadership:** potrzebuje modelu wpływu (wyczerpanie planet → suma influence). Ten sam
  mechanizm płatności jest w `production.py`/`objective_payment.py` — wydzielić wspólny
  „PaymentPicker" (wpływ vs zasoby) i użyć we wszystkich kartach z kosztem.
- **Diplomacy:** żeton innych graczy z REZERWY; brak żetonu w rezerwie → z command sheet
  (wybór gracza, więc to też PROMPT dla innych graczy, nie tylko aktywnego). Gracz, który
  już ma żeton w systemie, nic nie kładzie. Token „Diplomacy" tylko kosmetyka (RULES notatka).
- **Politics:** speaker zmienia się od razu (wpływa na `speaker_id` i kolejność); podgląd
  agendy jest prywatny. Ręka akcji >7 → odrzucanie (istniejący limit ręki).
- **Construction:** limity (1 dok / planeta, 2 PDS / planeta, Demilitarized Zone), brak
  jednostki w rezerwie → zdjęcie jednostki z systemu bez żetonu. **TE:** inny tekst
  („1 struktura" lub PRODUCTION doku) — inny zestaw kroków.
- **Warfare:** **TE** to w ogóle inna karta (akcja taktyczna bez żetonu) — wymaga wejścia
  w przepływ taktyczny z flagą „bez żetonu"; wyraźnie osobna implementacja.
- **Technology:** wymagania kolorów (`requirements` w assetach: B/BB, itd.), kolory z
  umiejętności/skipów, technologie frakcyjne (`faction`), ulepszenia jednostek
  (`baseUpgrade`), wyczerpywanie (`exhausted_technologies`). Zniżka zasobów z efektów
  (np. karty/frakcje) przez hooki.
- **Imperial:** punktowanie celu istnieje (`objectives.score_public`); trzeba je wywołać z
  kontekstu karty (bez kroku „status"). Tajny cel: limit 3 (łącznie z zapunktowanymi) →
  prompt zwrotu niezapunktowanego.

## 5. Które karty potrzebują dedykowanego UI

1. **Technology — TAK, osobny widok.** „Technology Research box": drzewo/siatka 4 kolorów
   (typy i kolory brać z assetów `types`/`requirements`, nie z pamięci) + technologie
   jednostkowe (szare) + frakcyjne. Stany kafla: posiadana / do zbadania (spełnione wymagania) /
   zablokowana (brakuje prerekwizytów, pokaż czego) / wyczerpana. Panel boczny: tekst
   technologii, koszt (primary: 0; druga: 6 zasobów; secondary: 4 zasoby + żeton), PaymentPicker.
   Reużywalne poza kartą strategii (zdolności typu „research a technology", Codex). **Największy element.**
2. **Politics — mały modal** (prywatny): wybór mówcy + podgląd 2 kart agendy z układem góra/dół.
3. **Wspólny PaymentPicker** (wpływ lub zasoby, wyczerpywanie planet) — Leadership, Technology;
   reuse z Production/Objective payment.
4. **Tryb wyboru na mapie** (system / własny żeton): Diplomacy, Construction (+secondary), Warfare.
   Reuse mechanizmu „activate mode" z akcji taktycznej.
5. **Selektory małe:** wybór gracza (Politics, Trade), puli żetonów (Leadership, Warfare),
   planet do odnowienia (Diplomacy), celu publicznego (Imperial), zwrotu tajnego celu.
6. **Tylko potwierdzenie (0):** secondary Trade/Politics/Imperial (po kosztach żetonu).

Wspólna powłoka: jeden komponent „Strategy Card Resolution" (dock/overlay) renderujący
bieżący `step` — po stronie respondenta pokazuje się popup follow/don't follow (już jest
`SecondaryDecisionModal`), a po „follow" ten sam overlay z krokami karty.

## 6. Proponowana kolejność wdrożenia

1. (GOTOWE) Walidacja jednej akcji na turę + UI wyszarza kartę po akcji/pasie.
2. Szkielet wieloetapowy (`pending_strategy`, kontrakt `decision`+`payload`, pobranie
   żetonu strategy pool, spasowani mogą follow, wyczerpanie po oknie) + testy.
3. Karty „czyste": Trade, Imperial, Politics (bez wpływu/płatności planet).
4. PaymentPicker + Leadership, Diplomacy.
5. Construction, Warfare (mapa + produkcja).
6. Technology (drzewo) — osobny blok, bo największe UI i model badania.
7. Warianty TE (Construction/Warfare) po decyzji, którego zestawu używamy.

## 7. Pytania do decyzji

- Który zestaw kart: PoK (obecnie kanoniczny w rejestrze) czy z TE (Construction/Warfare)?
- Timeout/auto-pass w sieci: kiedy ustalamy politykę (teraz hot-seat)?
- Czy Technology box ma być od razu uniwersalny (reuse dla innych źródeł badania)? Rekomendacja: tak.
