# Scena wyboru frakcji (setup) — projekt, pliki, treść

Dokument opisuje **aktualny stan** UI wyboru frakcji i kroku „Gracze" w kreatorze nowej gry
oraz to, jak dodawać treść (portrety, cytaty, lore) i jakich pułapek unikać. Historia
iteracji jest w `PROGRESS.md` / `PROGRESS_ARCHIWUM.md`; kod nadrzędny wobec tego opisu.

---

## 1. Przepływ kreatora

`StartScreen` (menu → „Graj") → `SetupWizard` z dwoma krokami (`setupSteps.ts`):

1. **`name-color` — „Gracze"** (`steps/Step_NameColor.tsx`): per gracz nazwa, kolor oraz
   **sterowanie Człowiek/Bot + poziom trudności bota** (zbiór trudności z `GET /engine/config`,
   nie z frontu). Osobny krok „Człowiek/bot" został usunięty. Walidacja sterowania siedzi w
   `validateStep("name-color")` (`useSetupStore.ts`). Liczba graczy i map string są
   w nagłówku kreatora tylko na pierwszym kroku.
2. **`faction` — scena pełnoekranowa** (`steps/Step_Faction.tsx`): wybór frakcji per gracz
   wraz z technologiami startowymi (wbudowane w `FactionSummary`). Krok jest w
   `STAGE_STEP_IDS` (`SetupWizard.tsx`), więc renderuje się **bez ramki kreatora** i sam
   rysuje pasek górny (Wstecz · przełącznik graczy · Start gry). `StartScreen` w trybie
   sceny zdejmuje padding/scroll kontenera (`.setupScreenStage`).

Obsidian nie jest wybieralny — wchodzi tylko przez przycisk „Zobacz Obsidian" w panelu
Firmamentu (`DERIVED_FACTION` w `FactionSummary.tsx`). Scena pokazuje wtedy jego portret/lore.

---

## 2. Układ sceny (od lewej do prawej)

```
┌ pasek górny: ← Wstecz │ Gracz1 Gracz2 … │ Start gry → ──────────────────────────┐
│ ┌ nagłówek (panel: ikona + nazwa + cytat + autor) ┐                              │
│        [ POSTAĆ ]──lore (2 kolumny, nachodzi na prawą, wygaszoną część postaci)  │ detail │ lista │
│                      ✦ Wybierz dla gracza N ✦  (przycisk na środku dołu)         │ (wąski)│ frakcji│
└────────────────────────────────────────────────────────────────────────────────────┘
```

- **Strefa postaci** (`.characterZone`, `Step_Faction.module.css`): portret przy lewej
  i dolnej krawędzi ekranu; prawa krawędź zanika maską. Zmienne CSS: `--portrait-w`
  (szerokość pasa), `--quote-h` (wysokość nagłówka; mniejsza bez cytatu), `--lore-top`,
  `--pick-h` (wysokość dolnego rzędu z przyciskiem), `--figure-cx` (środek **zmierzonej**
  sylwetki, ustawiany z JS).
- **Panel szczegółów** (`FactionSummary`): wąski (`clamp(280px, 18.5vw, 350px)`), szkło
  z blurem; zdolności, technologie, jednostki, liderzy, start gry. Pojawia się **szybko**.
- **Lista frakcji** (prawo): pionowa, z wyszukiwarką; **sam klik** zmienia podgląd
  (bez hover-popoverów — patrz gotcha „karta zostaje na hover"). Kafel „Losowa" wybiera od razu.
- **Przycisk „Wybierz dla gracza N"** (`.pickBar`): osobny, wyśrodkowany na dole, złoty;
  po wyborze „✓ Wybrana dla gracza N". Ostrzeżenie, gdy frakcję ma już inny gracz.
- Poniżej 1100 px strefa postaci jest ukryta, a kolumny układają się pionowo.

---

## 3. Pliki

| Plik | Odpowiedzialność |
|---|---|
| `domains/setup/steps/Step_Faction.tsx` + `.module.css` | Układ sceny, stan podglądu/gracza, lista, przycisk wyboru |
| `domains/setup/FactionBackdrop.tsx` + `.module.css` | Warstwy sceny: `FactionPortraitLayer`, `FactionHeader`, `FactionLore`, `splitLoreColumns`, akcent koloru |
| `domains/setup/GlyphText.tsx` + `.module.css` | Hook `useDecode` + `DecodedText` — pismo ↔ tekst czytelny (efekt rozszyfrowania) |
| `domains/setup/FactionSummary.tsx` + `.module.css` | Panel szczegółów frakcji (reużywa komponenty panelu gracza), podgląd frakcji pochodnej |
| `domains/setup/factionLore.ts` | **Treść**: cytaty, autorzy, lore, ścieżki portretów, `glyphLore`, `glitchPhrases` |
| `domains/setup/useSetupStore.ts`, `setupSteps.ts` | Stan i kroki kreatora, walidacja |
| `styles/fonts.css` | `@font-face`: Ambroise Firmin, Handel Gothic, Lazaxian |

`FactionBackdrop.tsx` jest długi (≈560 linii) — świadomie zostawiony w jednym pliku
(decyzja usera); podział lore do osobnego pliku to opcja na przyszłość.

---

## 4. Portret postaci

- Plik: `frontend/public/faction_portraits/<id>.{png,jpg,jpeg,webp}` (lub `portrait`
  w `factionLore.ts`). Łańcuch zapasowy: portret → bohater frakcji `/leaders/<heroId>.webp`
  → ikona frakcji (rysowana jako przygaszony symbol). Brak CDN.
- **Przezroczyste tło** (PNG postaci). Po `onLoad` `measureAlphaInset` (canvas, alfa > 16)
  mierzy przezroczysty margines od lewej/dołu oraz szerokość sylwetki. Korekta
  `transform: translate(%)` dosuwa **widoczną** sylwetkę do krawędzi ekranu, a środek
  sylwetki (`--figure-cx`) służy do centrowania nagłówka i ustawienia lore.
- Obraz ma box = widoczna treść (`width/height: auto` + `max-*`, bez `object-fit`),
  dzięki czemu przesunięcia w % są dokładne.

---

## 5. Nagłówek sceny (`FactionHeader`)

Panel w stylu nagłówka karty frakcji: ciemna płyta ze ściętymi rogami (`clip-path`),
obrys w **kolorze frakcji** (`--accent`), ikona po lewej, po prawej nazwa (Handel Gothic D
Bold), cytat (kursywa) i autor (`— Autor`, bez cudzysłowu). Tekst wyśrodkowany względem
siebie; cały panel wyśrodkowany nad zmierzoną sylwetką; box przylega do tekstu
(bez `text-wrap: balance`).

- **Akcent koloru**: wyliczany z lokalnej ikony `/static/factions/<id>.png`
  (`useFactionAccent` — średnia ważona nasyceniem → `hsl(hue 72% 58%)`, cache po id).
  Szara ikona → bursztyn. Żadnych kolorów wpisanych na sztywno.
- **Cytat**: w `factionLore.ts` wpisuj `quote` **bez cudzysłowu** (komponent dodaje “ ”;
  jeśli wkleisz z cudzysłowem — zdejmie je z brzegów). `quoteAuthor` — sam autor; wiodący
  myślnik jest opcjonalny (komponent doda „— "). Autor pokazuje się tylko z cytatem.

---

## 6. Lore (`FactionLore`)

- **Dwie jawne kolumny** (`splitLoreColumns`), obie zaczynają się na tej samej wysokości.
  Podział wg liczby znaków; jeśli środek wypada w długim akapicie, cięcie następuje na
  końcu zdania; śródtytuł nie zostaje sam na dole kolumny. (Wcześniej CSS `column-count`
  — odrzucone: nierówne kolumny, rozdarte akapity.)
- **Auto-dopasowanie czcionki** do boxa: binarne szukanie największego rozmiaru
  (limit zależny od okna: `min(21, max(14, min(1.15vw, 2.1vh)))`, min 10.5 px), który
  mieści się **bez przewijania** (test tylko wysokości — test szerokości zawodził przez
  `::before` wystające poza `article`). Przelicza się przy zmianie rozmiaru strefy i fontów.
- Lore zaczyna się przy prawej krawędzi sylwetki i **delikatnie na nią nachodzi**
  (`margin-left` z `--figure-cx`), tło lore jest lekkie i przezroczyste.
- Bloki w `lore`: `paragraph` / `heading` / `quote`; opcjonalnie `tone` (`red`/`dark-red`)
  i `size` (`large`/`small`).

---

## 7. Animacje (kolejność uwagi)

Tempo jest **celowo zróżnicowane**: oprawa wolna, informacja robocza szybka.

| Element | Start | Czas |
|---|---|---|
| Postać (krycie + przesunięcie + jasność; **rozmycie schodzi osobno w 2.2 s**) | 0.25 s | 5.5 s |
| Panel nagłówka → nazwa → cytat → autor | 0.4 / 0.5 / 1.5 / 2.8 s | 1.6–2.2 s |
| Lore (blok po bloku, 230 ms/blok) + jego tło | od 4.2 s | 2.4 s |
| Panel szczegółów (nagłówek + sekcje) | 0.05–0.6 s | 0.4–0.45 s |
| Przycisk wyboru | 0.4 s | 0.9 s |

**Gdzie stroić tempo:** blok zmiennych `--t-*` na początku `.stage` w
`steps/Step_Faction.module.css` (z opisem każdej). Mniejsza liczba = szybciej. Kluczowe:
`--t-portrait-fade` (całe wyłanianie postaci), `--t-portrait-unblur` (jak długo postać jest
rozmyta — osobna animacja `portraitUnblur`, domyślnie 2.2 s), `--t-quote-delay`,
`--t-lore-delay`, `--t-lore-step`, `--t-detail-*`, `--t-pick-*`. Kształt samych animacji
(ruch, kolejne etapy krycia/jasności) jest w `@keyframes` w `FactionBackdrop.module.css`
(`portraitFade`, `portraitUnblur`, `portraitGrade`, `headIn`, `loreIn`) i `FactionSummary.module.css`
(`sectionIn`). Postać składa się z trzech animacji na różnych właściwościach (warstwa:
krycie/ruch + rozmycie; obrazek: jasność), dlatego rozmycie można skrócić niezależnie.

Wszystko odtwarza się przy każdej zmianie frakcji (`key` na warstwach).
`prefers-reduced-motion`: bez ruchu/blura, ale **zostaje wolny, widoczny fade** (krótki fade
sprawiał, że animacji „nie było widać"); panel szczegółów dostaje krótki fade.

---

## 8. Lore pisane pismem z gry — Obsidian (`glyphLore`)

Obsidian ma w `factionLore.ts` flagę `glyphLore: true`:

- Tekst (wielkie litery, angielski) wyświetlany krojem **Lazaxian** (`GlyphText.module.css`).
  Przycisk **„Przetłumacz" / „Pokaż oryginał"** przełącza na czytelny szeryfowy krój.
- **Efekt rozszyfrowania** (`useDecode`, ~3.6 s): fala idzie blok po bloku, w bloku znak po
  znaku; przed frontem znaki migoczą (część podmieniana na losowe litery), na froncie
  świeci czerwony „kursor"; box drży, tekst dostaje aberrację czerwono-cyjanową, przez
  box przesuwa się pasmo ze skanlinami. Losowość deterministyczna (hash klatki).
  Dopasowanie czcionki robi się dopiero po zakończeniu przejścia (`busy`).
- **Groza (tylko `glyphLore`)** — timery w `FactionLore`, wstrzymane w trakcie
  rozszyfrowania i przy reduced-motion: losowy glitch akapitu (Web Animations API: skos,
  rozdwojenie kolorów, ucięte pasy), przygasanie całego lore, krótki **błysk frazy** z
  `glitchPhrases` w losowym miejscu oraz „bijące serce" (puls tła). Frazy autorstwa projektu
  — do edycji w `factionLore.ts`.
- Transkrypcja lore jest fanowska: ligatury `(TH)` zdjęte, uwagi usunięte, nieczytelne
  fragmenty pominięte (m.in. „WHEN YOU'VE FINISHED PLAYING…", „EVERY TENTH CLOSE?",
  „LIFE BRINGS DEAD", „THE WORLD DRAWS ??P"). Uzupełniaj w `factionLore.ts`.

---

## 9. Gotchas (czego nie robić)

- **Web Animations API: `easing` w `animate(keyframes, {easing})` działa na CAŁY przebieg**,
  nie na krok. `steps(1, end)` tam trzyma animację w pierwszej klatce do końca → efekt
  niewidoczny. Skokowość ustawiaj `easing` **w każdej klatce kluczowej**.
- **Nie podmieniaj właściwości `animation` na elemencie z animacją wejścia** (np. dodając
  klasę „glitch"): po zdjęciu klasy animacja wejścia restartuje się i tekst znów znika.
  Efekty chwilowe rób przez WAAPI (nakłada się na animacje CSS bez restartu).
- **`text-wrap: balance`** skraca linie, ale nie kontener — box zostaje szeroki. Dla boxa
  przylegającego do tekstu zostaw zwykłe zawijanie.
- Nie mierz szerokości `article` z pseudo-elementem wystającym (`::before` z ujemnym `inset`).
- Układ wyśrodkowany względem **zmierzonej sylwetki**, nie pasa portretu (postać bywa węższa
  → przesunięcie w prawo).
- Hover-popover nad przewijaną listą bywa „przyklejony" — stąd klik zamiast hovera.
- Niebieski = sygnał interakcji (zaznaczenie, focus), nie dekoracja; dekoracje w cieple TI4.
  Bez ozdobnych pasków/linii u góry ekranu.

---

## 10. Pliki zewnętrzne i licencje

- Fonty (`frontend/public/font/`): **Ambroise Firmin Bold**, **Handel Gothic D Bold**,
  **Lazaxian-Bold.ttf** — kroje komercyjne/fanowskie; commit decyduje właściciel repo.
  Brak pliku nie psuje UI (spadek na kolejny krój ze stosu `font-family`).
  `@font-face` w `styles/fonts.css`.
- Portrety: `frontend/public/faction_portraits/` (m.in. `obsidian.png`, `firmament.png`
  mogą być jeszcze niezacommitowane w lokalnej kopii).

---

## 11. QA

Brak testów jednostkowych frontu. Po zmianie: `npm run type-check` (lub `npx tsc --noEmit`),
`npm run lint`, `npm run build` w `frontend/`. Efekty wizualne (animacje, glitche,
centrowanie) weryfikuje się wyłącznie w przeglądarce.
