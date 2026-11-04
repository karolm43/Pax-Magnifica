# Portrety frakcji (ekran wyboru frakcji w setupie)

Wrzucaj tu obrazki portretów frakcji. Nazwa pliku = identyfikator frakcji
(`faction.id`), rozszerzenie: `.jpg`, `.png` lub `.webp`.

Przykłady:

- `ghost.jpg`   → The Ghosts of Creuss
- `argent.png`  → Argent Flight
- `sol.webp`    → The Federation of Sol

Komponent `FactionSummary` próbuje ścieżek w kolejności: `.jpg` → `.png` → `.webp`.
Jeśli żaden plik nie istnieje, pokazuje placeholder (ikonę frakcji) — to nie błąd.

Własną (niestandardową) ścieżkę portretu możesz podać w
`frontend/src/domains/setup/factionLore.ts` w polu `portrait` danej frakcji.

Lore (tekst) uzupełniasz w tym samym pliku `factionLore.ts` w mapie `FACTION_LORE`.

Wyj�tek: trzy warianty Keleres (keleresm/keleresx/keleresa) u�ywaj� jednego pliku keleres.png.
