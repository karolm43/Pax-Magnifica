# Claude Code — wejście do projektu

Zasady projektu są w pliku steering (wspólnym z Kiro) i obowiązują w całości:

@.kiro/steering/custodian-engine.md

## Uwagi praktyczne dla Claude Code

- Start sesji: `docs/README.md` (indeks). Duże pliki (`docs/PROGRESS.md`, `docs/RULES.md`,
  `docs/PROGRESS_ARCHIWUM.md`) czytaj punktowo (grep/offset), nigdy w całości.
- QA backendu: `uv run pytest -q` ; `uv run ruff check src tests` ; `uv run mypy src tests`.
  QA frontu (w `frontend/`): `npm run type-check` ; `npm run lint` ; `npm run build` ; `npx vitest --run`.
- W repo może równolegle pracować inna sesja (Kiro / inny agent): przed commitem sprawdź `git status`
  i staguj WYŁĄCZNIE własne zmiany — w plikach mieszanych tylko własne hunki, nie cały plik.
- Czas rzeczywisty w logice gry: nigdy `time.time()` w `core/` — wstrzykuj `now` (wzór: `core/game_clock.py`,
  `create_app(now=...)`).
