# Claude Code — wejście do projektu

Zasady projektu są w pliku steering (wspólnym z Kiro) i obowiązują w całości:

@.kiro/steering/custodian-engine.md

## Uwagi praktyczne dla Claude Code

- Start sesji: `docs/README.md` (indeks). Duże pliki (`docs/PROGRESS.md`, `docs/RULES.md`,
  `docs/PROGRESS_ARCHIWUM.md`) czytaj punktowo (grep/offset), nigdy w całości.
- **Wspomnienia Kiro** (gotchas, decyzje użytkownika, stan modułów — ~85 wpisów) leżą w
  `~/.kiro/memories/memories.db`. Przed zadaniem przeszukaj je pod kątem tematu:
  `uv run python scripts/kiro_memories.py search <słowo> [...]`, potem `... show <tytuł>`.
  Tylko odczyt — nie kopiuj ich do własnej pamięci (źródłem prawdy zostaje baza Kiro).
- QA backendu: `uv run pytest -q -n auto` (równolegle; w trakcie pracy `uv run pytest -q --testmon`
  = tylko testy dotknięte zmianą) ; `uv run ruff check src tests` ; `uv run mypy src tests`.
  QA frontu (w `frontend/`): `npx tsc --noEmit -p tsconfig.app.json` (UWAGA: `npm run type-check`
  NIE sprawdza `src/`) ; `npm run lint` ; `npm run build` ; `npx vitest --run`.
- Stan gry żyje tylko w pamięci backendu — restart kasuje grę użytkownika. Nowe trasy/pola wymagają
  restartu, więc uprzedź użytkownika zamiast restartować samemu.
- W repo może równolegle pracować inna sesja (Kiro / inny agent): przed commitem sprawdź `git status`
  i staguj WYŁĄCZNIE własne zmiany — w plikach mieszanych tylko własne hunki, nie cały plik.
- Czas rzeczywisty w logice gry: nigdy `time.time()` w `core/` — wstrzykuj `now` (wzór: `core/game_clock.py`,
  `create_app(now=...)`).
