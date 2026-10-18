# Custodian Engine — Frontend (Tabletop UI)

Mapa SVG Twilight Imperium w React 19 + Vite + TypeScript, połączona z backendem
FastAPI przez REST i WebSocket (stan synchronizowany w store Zustand).

## Stack

- React 19 + TypeScript 5
- Vite 8 (dev-serwer + proxy do backendu)
- Zustand 5 (zarządzanie stanem, synchronizacja przez WebSocket)
- Tailwind CSS 4 (plugin `@tailwindcss/vite`)
- SVG (render mapy heksagonalnej na współrzędnych kubicznych)

> shadcn/ui dojdzie w Bloku 4 (panele edycji / Action Wizards).

## Uruchomienie (development)

Potrzebne są DWA procesy w osobnych terminalach:

1. Backend (z katalogu głównego repo):
   ```powershell
   uv run python -m src.api
   ```
   Serwer FastAPI na `http://127.0.0.1:8000`.

2. Frontend (z katalogu `frontend/`):
   ```powershell
   npm install   # tylko za pierwszym razem
   npm run dev
   ```
   Dev-serwer Vite na `http://localhost:5173`. Zapytania `/api/*` i `/ws` są
   proxowane do backendu (patrz `vite.config.ts`), więc front łączy się przez
   adresy względne.

## Build produkcyjny

```powershell
npm run build     # tsc -b && vite build -> dist/
npm run preview   # podgląd builda
```

## Struktura

```
frontend/
├─ index.html
├─ vite.config.ts        # plugin React + Tailwind + proxy /api i /ws
├─ src/
│  ├─ main.tsx           # punkt wejścia
│  ├─ App.tsx            # layout: pasek stanu + mapa, Undo/Redo
│  ├─ HexMap.tsx         # renderer SVG (kafelki + krawędzie sąsiedztwa)
│  ├─ hex.ts             # (q,r,s) -> piksele (pointy-top)
│  ├─ store.ts           # Zustand: połączenie, stan gry, historia
│  ├─ api.ts             # REST + WebSocket (adresy względne)
│  └─ types.ts           # kontrakt DTO (odpowiada src/api/schemas.py)
```

## Kontrakt z backendem

Typy w `src/types.ts` odpowiadają schematom Pydantic w `src/api/schemas.py`.
Przy zmianie DTO po stronie backendu zaktualizuj te typy ręcznie.
