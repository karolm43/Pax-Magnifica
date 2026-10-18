# Custodian Engine — frontend

Viewer planszy Twilight Imperium 4 dla Custodian Engine. Oparty na kodzie
AsyncTI4 `ti4_web` (React 19 + Vite + TypeScript), zredukowany do **pojedynczego
widoku jednej, lokalnej gry** (bez landing page'a, listy gier, logowania).

Frontend jest **viewerem**: pobiera jeden dokument `web-data` z backendu i renderuje
z niego planszę oraz panele graczy. Źródłem prawdy o stanie gry jest backend (`src/`).

## Uruchomienie

```bash
npm install        # pierwszy raz
npm run dev        # Vite na http://localhost:5173
```

Backend musi działać równolegle (`uv run python -m src.api` w katalogu repo).
Proxy Vite kieruje `/bot` i `/static` do backendu na `:8000` (patrz `vite.config.ts`).
Root `/` otwiera od razu widok gry.

## QA

```bash
npm run type-check   # tsc --noEmit
npm run lint         # eslint
npm run build        # tsc && vite build
```

## Jak to działa (skrót)

- Wejście: `src/main.tsx` → `pages/GameMapPage.tsx` (`gameId` domyślny = `"local"`).
- Dane: `src/api/usePlayerData.ts` pobiera `GET /bot/api/public/game/{id}/web-data`.
- Statyczne katalogi (systemy/jednostki/planety) są WBUDOWANE w `src/entities/data/`.
- Grafiki idą z CDN AsyncTI4 (`src/entities/data/cdnImage.ts`).
- Branding (lewy róg): `src/shared/ui/Logo.tsx`.

Pełny opis architektury, kontraktu `web-data` i luk: **`../docs/ARCHITEKTURA_PO_MIGRACJI.md`**.
```
