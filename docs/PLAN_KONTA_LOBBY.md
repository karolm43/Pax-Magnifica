# Plan: konta, historia gier, lobby, tryby przygotowania partii

Stan: 2026-11-23. Menu główne przebudowane (`frontend/src/pages/MainMenu.tsx`), w lobby sekcja „Setup method”
(tylko Standard aktywny). Konta i drafty — PLAN, nic z tego nie jest jeszcze w kodzie.

## Cel (decyzja użytkownika 2026-11-23)

- Każdy gracz ma konto; historia gier i statystyki per konto.
- Lobby z ustawieniami partii (host zmienia, goście widzą na żywo — już działa przez `api/lobby_draft.py`).
- Wybór sposobu przygotowania partii: Standard (dziś), Full random, Milty Draft, Franken Draft (później).

## Podział odpowiedzialności

| Co | Gdzie | Dlaczego |
|---|---|---|
| Logowanie (email magic link, Discord/Google) | Supabase Auth | gotowe, bezpieczne, bez własnych haseł |
| Profile, historia gier, wyniki | Supabase Postgres (tabele + RLS) | trwałe, dostępne z każdego komputera |
| Stan partii, reguły, lobby na żywo | NASZ backend (Python) — bez zmian | silnik = sędzia; Supabase nie zna reguł |
| Pliki zapisów (`saves/*.db`) | lokalnie u hosta — bez zmian | duże migawki, Undo; nie ma sensu ich wysyłać |

Zasady bezpieczeństwa:
- Front zna tylko `anon`/publishable key (jawny z definicji; chroni go RLS).
- Klucz `service_role`/secret TYLKO w backendzie (`.env` w katalogu głównym, w `.gitignore`). Nigdy w `frontend/`.
- Backend weryfikuje token Supabase (JWT) przez JWKS projektu
  (`https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`) — `user_id` z tokenu zastępuje dzisiejsze
  „dołącz imieniem” (`/lobby/join`). Token miejsca (`api/seats.py`) zostaje jako mechanizm sesji przy stole.
- Wyniki partii zapisuje WYŁĄCZNIE backend (service_role), nie klient — inaczej każdy mógłby dopisać sobie zwycięstwo.

## Schemat bazy (szkic — migracja SQL powstanie razem z kodem)

- `profiles` (id = `auth.users.id`, display_name, avatar_url, created_at) — czyta każdy zalogowany, zmienia właściciel.
- `games` (id, created_at, finished_at, host_id, setup_method, map_string, player_count, round_count, winner_id).
- `game_players` (game_id, profile_id NULL dla bota, seat, faction, color, is_bot, final_vp, placement).
- RLS: gracz widzi gry, w których brał udział; zapis tylko przez service_role.

## Etapy

1. **K1 — logowanie**: `@supabase/supabase-js` we froncie, `ProfileChip` w menu (dziś „Guest” + nieaktywne
   „Sign in”), ekran logowania. Bez konta da się grać dalej jako gość (lokalnie, z botami).
2. **K2 — tożsamość w lobby**: backend weryfikuje JWT, gość dołącza kontem (nazwa z profilu), host widzi awatary.
3. **K3 — historia**: przy końcu gry (`victory`/epilog) backend zapisuje `games` + `game_players`; pozycja menu
   „Game history” (dziś „Soon”) + ekran historii i prostych statystyk (frakcje, zwycięstwa).
4. **D1… — drafty**: wybór w `useSetupStore` + szkic lobby (`lobby_draft.py`), krok draftu w `setupSteps.ts`.
   Reguły Milty Draft najpierw do `docs/rules/` ze źródłem (AsyncTI4 / tirules2), potem kod.

## Instrukcja dla użytkownika (Supabase)

1. supabase.com → konto → **New project** (region: Central EU / Frankfurt; zapisz hasło bazy).
2. **Project Settings → API**: skopiuj *Project URL* i *anon / publishable key*. Klucz *service_role / secret*
   tylko wpisz do `.env` (nie wysyłaj nikomu, nie commituj).
3. **Authentication → Sign In / Providers**: Email włączony (magic link). Opcjonalnie Discord: aplikacja w Discord
   Developer Portal → OAuth2 → Redirect `https://<ref>.supabase.co/auth/v1/callback`; Client ID/Secret wklej w Supabase.
4. **Authentication → URL Configuration**: Site URL `http://localhost:5173`; Redirect URLs:
   `http://localhost:5173/**` oraz adresy ZeroTier/LAN, z których grają znajomi (np. `http://10.147.19.174:5173/**`).
5. Pliki (oba poza gitem):
   - `frontend/.env.local`: `VITE_SUPABASE_URL=…`, `VITE_SUPABASE_ANON_KEY=…`
   - `.env` (katalog główny): `SUPABASE_URL=…`, `SUPABASE_SERVICE_ROLE_KEY=…`
6. Daj znać, że gotowe (URL i anon key można podać w rozmowie; service_role — nie).
