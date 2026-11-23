# Plan: okna decyzji — spójność, czytelność, mniej clutteru

Stan: 2026-11-23. Podstawa: przegląd kodu + zrzuty z izolowanej gry (Sol + 5 botów, Leadership,
karta akcji, technologia, faza statusu, faza agendy). Realizacja blokami U1–U6; każdy blok = kod +
testy + sekcja w `PROGRESS.md` + commit.

## Zasady docelowe (jeden wzorzec dla wszystkich okien)

1. **Jedna decyzja na ekranie naraz.** Okna decyzji zajmują jedno miejsce ("strefa decyzji");
   kolejne czekają w kolejce jako licznik „+N more", nie jako drugie okno.
2. **Jedna rama okna** (`DecisionFrame`): nagłówek = chip komponentu (ten sam co w panelu gracza,
   ⓘ po kliknięciu) + plakietka rodzaju (Primary / Secondary / Action card / Required);
   treść = pełny tekst normalnym kolorem; pola; stopka = [Never ask] [Skip/Cancel Esc] [Akcja Enter].
   Bez drugiego tytułu nad ramą.
3. **Jeden zestaw widżetów:** jeden `Stepper`, jedna płatność (`Payment`), jeden rozdział żetonów
   (`CommandPools`), jeden kafelek opcji (`Tile`). „Auto" zawsze w tym samym miejscu i stylu
   (przycisk pomocniczy przy polu; akcja główna zawsze w stopce, najmocniejszy kolor).
4. **Każda informacja raz.** Kto decyduje — w ramie okna (nie dodatkowo w panelu bocznym i pasku);
   liczby (głosy, kolejka) — w jednym miejscu.
5. **Nic nie zasłania okna decyzji**: dymki planet, toasty reakcji, dok ręki, panel „Decisions"
   ustępują strefie decyzji.
   6. przydało by sie jeszcze przebudować jak czegoś nie robisz np nie uzywasz hero do not place jest to zbyt nieczytelne 

## Co pokazały zrzuty (dowody)

| # | Miejsce | Problem |
|---|---------|---------|
| Z1 | Faza statusu | Dwa okna decyzji naraz: panel statusu (Sol) + oferta Mitosis (Arborec), do tego panel „Reaction window”, taca Effects i karta „PLAYED” |
| Z2 | Agenda | Panel „Decisions / Timing windows” leży na tekście karty Ballot (nieczytelny); toast reakcji zasłania listę Senatu i wyniki; dok ręki zasłania dół wyników |
| Z3 | Agenda | „Głosy dostępne” pokazane 3×: łuk Senatu + lista pod łukiem, lista miejsc „N to spend”, każdy wynik „N votes available”; „Agenda 1 of 2” 2× |
| Z4 | Leadership primary/secondary | Podwójny nagłówek: „STRATEGIC ACTION” / „STRATEGY CARD — SECONDARY ABILITY” + rama „Leadership PRIMARY” |
| Z5 | Leadership | Rozdział żetonów bez „Auto”; inny wygląd niż `CommandPools` w fazie statusu (wiersze vs kolumny) |
| Z6 | Faza statusu | „Auto” pomarańczowe i mocniejsze niż „Confirm”; w innych oknach „Auto” jest subtelne |
| Z7 | Secondary Leadership | „Follow” dostępne, choć gracz ma 2 wpływu (nic nie kupi) → ślepa uliczka z samym „Back” |
| Z8 | Secondary | Respondent pokazany 3× (pasek górny, panel boczny „Responding”, okno „Your call”); kolejka 2× („Remaining in queue: 5” i „Remaining after you: 4”) |
| Z9 | Component action | Lista dubluje karty akcji widoczne w ręce; tekst wstępu nieaktualny; brak opisu i ⓘ |
| Z10 | Sling Relay | Dymek planety (Mecatol Rex) wyskakuje nad formularzem i zasłania pole wyboru |
| Z11 | Modale użycia (karta/tech/lider/legendarna) | Tekst karty szary (`dimmed`), tytuł gołym tekstem zamiast chipu, brak Enter/Esc |
| Z12 | Oferta Mitosis | Tytuł „Mitosis” 2× (nagłówek + etykieta pola); tekst dwóch zdolności sklejony bez kropki („…infantry At the start…”); plakietka „Required” prawie niewidoczna |
| Z13 | Pasek/coach | W fazie statusu pasek mówi „take a turn”; coach „What now?” w trybie testowym mówi „Watch the map”, choć to tura gracza; powiadomienie „Player p1 revealed…” zamiast nazwy frakcji |
| Z14 | Planszy brak | Przy otwartym oknie strategii plansza prawie niewidoczna: lewy panel + okno + prawy panel + dok ręki + strefa kart strategii |

## Bloki realizacji

### U1 — Wspólna rama okna decyzji (fundament)
- `shared/ui/DecisionFrame` wyciągnięty z `OfferDock`: nagłówek z chipem komponentu
  (`Tech`, `ComponentInfoButton`, karta strategii po `ComponentRef`), plakietki, tekst
  (normalny kolor, zwijanie > 420 znaków), slot pól, stopka z Enter/Esc.
- Przepiąć: `OfferDock`, `ActionCardPlayModal`, `TechnologyUseModal`, `LegendaryUseModal`,
  `FactionComponentUseModal` (4 modale → jeden `ComponentUseModal` + konfiguracja rodzaju).
- `PromptShell` kart strategii = `DecisionFrame`; usunąć tytuł `AppModal` (Z4).
- Jednolite teksty: „Cancel”, „Use”, jeden komunikat braku celów; wyczerpane = komunikat
  zamiast formularza (Z11).
- Testy: vitest ramy (Enter/Esc, Required, chip), aktualizacja testów modali; e2e (komponent
  montowany zawsze).

### U2 — Jeden zestaw widżetów
- Jeden `Stepper` (z `DecisionTiles`) zamiast 5 kopii (PromptParts, TradingTable,
  RemovalWindowModal, CommandPools).
- Płatność: jeden widżet = kafelki (`PaymentField`); `PaymentPicker` (karty planet z Leadership)
  usunąć (decyzja P1). Leadership: bez wymogu wielokrotności 3 + „Auto”.
- Rozdział żetonów: `CommandPools` wszędzie (Leadership, Warfare, Predictive Intelligence, status),
  zawsze z „Auto” (Z5).
- „Auto”: jeden komponent `AutoButton`, zawsze przy polu, styl pomocniczy; główna akcja w stopce
  (Z6). Dodać brakujące: `multi`, Leadership (cel = pełne wielokrotności 3), głosowanie agendy.

### U3 — Strefa decyzji i kolejka (clutter)
- Jedna strefa decyzji: jeśli otwarte jest okno fazy (status, agenda, karta strategii), oferty
  własne wchodzą do niego jako kolejny krok lub czekają jako „+N”, nie jako drugie okno (Z1).
- Panel „Decisions / Timing windows” chowa się, gdy działa okno decyzji, i nie zachodzi na
  overlay agendy (Z2).
- Toast reakcji i dymki mapy nie zachodzą na okno decyzji (warstwa z-index + pozycja) (Z2, Z10).
- Dok ręki zwija się, gdy okno decyzji go przykrywa.
- **Stan (2026-11-23): zrobione** — znaczniki `data-decision-zone` / `data-phase-window`
  (`hooks/useDecisionZone.ts`); oferty przy oknie fazy czekają jako pastylka „+N” (nie jako krok
  wewnątrz okna fazy); baner reakcji przy oknie decyzji jedzie na górę.

### U4 — Usunięcie duplikatów informacji
- Respondent: tylko w ramie okna; panel boczny pokazuje kolejkę bez „Responding” (Z8).
- Agenda: jedno miejsce na „głosy dostępne” (proponuję: lista miejsc Senatu); z wyników usunąć
  „N votes available”; licznik agend tylko w nagłówku (Z3). Tiebreak = klik na podium.
- Kafelki: usunąć natywne `title` (dymek przez ⓘ i Tooltip). Oferta: etykieta pola nie powtarza
  tytułu (Z12).
- Component action: tylko komponenty spoza ręki (karty akcji = przeciąganie), opis + ⓘ (Z9).
- **Stan (2026-11-23): zrobione** — patrz `PROGRESS.md` (U4).

### U5 — Czytelność i ślepe uliczki
- Secondary: koszt follow jako osobna wyraźna linia; „Follow” nieaktywne z powodem, gdy nie da
  się nic uzyskać (Leadership < 3 wpływu) (Z7).
- `Required` czytelną plakietką; tekst zdolności z separatorami (backend: łączenie tekstów) (Z12).
- Pasek statusu i coach zgodne z fazą i trybem testowym; nazwy frakcji zamiast „Player p1” (Z13).
- Leadership: `base_gain` z silnika zamiast stałej 3.

### U6 — Wybór planet tylko na mapie (zasady użytkownika)
- Agenda „Elect Planet”: wybór wyniku klikiem na mapie (podświetlone planety) + lista wyników
  tylko jako podgląd głosów.
- DecisionFields: zamiast `Select`/`MultiSelect` → siatka dużych chipów, drag/klik zamiast list (decyzja P2).

## Decyzje użytkownika (odpowiedzi na pytania)
- **P1 — Płatność: ujednolicić, ma być ładna.** Wygląd z Leadership (wiersze/karty planet) NIE podoba się
  użytkownikowi „wcale” — usunąć. Jeden widżet płatności w całej grze = kompaktowe kafelki z wartością
  (wzór ofert/`PaymentField`), spójny z resztą. W Leadership:
  - USUNĄĆ ograniczenie „płacić można tylko po 3 influence” (dowolna kwota; liczba żetonów = `base_gain`
    z silnika wg reguły karty, nie wymuszone wielokrotności 3 w UI),
  - DODAĆ „Auto” (sensowna domyślna kwota/rozdział; ⚠️ ZAŁOŻENIE wpisać do `rules/R<NN>.md`).
- **P2 — Wiele opcji (>18) nie-planet/nie-tech: najwygodniej, preferować przeciąganie i klikanie, nie listy.**
  Siatka dużych klikalnych chipów (bez `Select`/`MultiSelect`), tam gdzie sensowne drag&drop; wyszukiwarka/
  grupowanie tylko pomocniczo. Zasada ogólna dla wszystkich okien: drag/klik > lista.
- **Kolejka decyzji = „kolejka do Twojej decyzji”.** Oczekujące decyzje gracza stoją w kolejce widocznej
  jako licznik „+N” przy jednym otwartym oknie (pkt 1 zasad); nie jako dodatkowe okna ani osobna lista
  (Z1, Z8). Kolejność obsługi = kolejność nadejścia, gracz decyduje po kolei.
- **P3** Kolejność bloków bez zmian: U1 → U2 → U3 → U4 → U5 → U6 (U2 zawiera powyższe zmiany płatności
  i Leadership; U5 „`base_gain` z silnika” dotyczy tego samego miejsca).
