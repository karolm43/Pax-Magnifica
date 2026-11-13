/*
 * Fonty tekstu i danych — IBM Plex Sans (UI) i IBM Plex Mono (liczby) z pakietów
 * @fontsource (dokładnie przypięte wersje w package.json). Bundlowane przez Vite
 * jako lokalne pliki .woff2 — ZERO żądań do Google Fonts / gstatic. Importujemy
 * tylko wagi z drabiny typograficznej (typography.css): Sans 400/500/600/700,
 * Mono 400/500/700. Podzbiory `latin` + `latin-ext` dają polskie znaki (ą, ę, ł…).
 */
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-sans/latin-700.css";
import "@fontsource/ibm-plex-sans/latin-ext-400.css";
import "@fontsource/ibm-plex-sans/latin-ext-500.css";
import "@fontsource/ibm-plex-sans/latin-ext-600.css";
import "@fontsource/ibm-plex-sans/latin-ext-700.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "@fontsource/ibm-plex-mono/latin-700.css";
import "@fontsource/ibm-plex-mono/latin-ext-400.css";
import "@fontsource/ibm-plex-mono/latin-ext-500.css";
import "@fontsource/ibm-plex-mono/latin-ext-700.css";

import "./ds/tokens.css";
import "./ds/base.css";
import "./styles/fonts.css";
import "./styles/gradients.css";
import "./styles/theme.css";
import "./styles/overlays.css";
import "./styles/tiChrome.css";
import "./styles/mobile.css";
import "./styles/zIndexVariables.css";

import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StartScreen from "./pages/StartScreen";
import GameMapPage from "./pages/GameMapPage";
import { isMobileDevice } from "./utils/isTouchDevice";
import { getPortalRoot } from "./ds";
import { playUi } from "./shared/audio/uiSounds";
import { installActorIdentity } from "./api/actorIdentity";
import { installConsoleCapture } from "./domains/bug-report/consoleCapture";

// Tożsamość aktora (RULES.md 44.1a): `?seat=<player_id>` → nagłówek X-Actor-Id do backendu.
installActorIdentity();
// Bufor ostatnich błędów konsoli do zgłoszeń „Report bug".
installConsoleCapture();

// Odrzucona akcja (np. nielegalny ruch -> HTTP 422) daje krótki dźwięk „error”.
const queryClient = new QueryClient({
  mutationCache: new MutationCache({ onError: () => playUi("error") }),
});

/*
 * Custodian Engine: jedna lokalna gra. Root ("/") to ekran startowy (wybór
 * graczy, frakcji, map stringa → utworzenie gry). Widok planszy jest pod
 * "/game" (gameId stały "local" — backend trzyma pojedynczy stan).
 */
const router = createBrowserRouter([
  {
    path: "/",
    element: <StartScreen />,
  },
  {
    path: "/game",
    element: <GameMapPage />,
  },
  {
    path: "/game/:mapid",
    element: <GameMapPage />,
  },
  {
    path: "/system/:systemId",
    lazy: () =>
      import("./domains/map/components/SystemTilePage/SystemTilePage").then(
        (m) => ({ Component: m.SystemTilePage }),
      ),
  },
  {
    path: "/rules",
    lazy: () =>
      import("./domains/rules/RulesBrowserPage").then((m) => ({
        Component: m.RulesBrowserPage,
      })),
  },
  {
    path: "/rules/:slug",
    lazy: () =>
      import("./domains/rules/RulesBrowserPage").then((m) => ({
        Component: m.RulesBrowserPage,
      })),
  },
]);

document.body.classList.toggle("mobile", isMobileDevice());

/*
 * Every overlay portals into this one node (see ds/overlays.tsx), so closed
 * popovers and tooltips never leave a trail of empty divs on <body>.
 */
getPortalRoot();

/*
 * A note for anyone who opens the console. This audience is unusually likely to
 * read the source, so the easter egg is a genuinely useful signpost rather than a
 * joke or a recruiting pitch — the reward for curiosity is knowing where to look.
 */
function printConsoleSignature() {
  console.log(
    "%cCUSTODIAN ENGINE%c  lokalny asystent / AI do Twilight Imperium 4",
    "font-weight:700;letter-spacing:0.12em;color:#e2e8f0;background:#0b0b0c;padding:3px 7px;border-radius:2px",
    "color:#868e96"
  );
}

printConsoleSignature();

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement,
);
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
