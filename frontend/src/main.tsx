import "./ds/tokens.css";
import "./ds/base.css";
import "./styles/fonts.css";
import "./styles/gradients.css";
import "./styles/theme.css";
import "./styles/overlays.css";
import "./styles/mobile.css";
import "./styles/zIndexVariables.css";

import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GameMapPage from "./pages/GameMapPage";
import { isMobileDevice } from "./utils/isTouchDevice";
import { getPortalRoot } from "./ds";

const queryClient = new QueryClient();

/*
 * Custodian Engine: aplikacja obsługuje JEDNĄ lokalną grę. Nie ma landing page'a,
 * listy gier ani logowania — root otwiera od razu widok gry. ``gameId`` jest stały
 * (``local``); backend trzyma pojedynczy stan i ignoruje identyfikator.
 */
const router = createBrowserRouter([
  {
    path: "/",
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
    "%cASYNC TI4%c  fan project for Twilight Imperium\u2122 \u00b7 play-by-Discord",
    "font-weight:700;letter-spacing:0.12em;color:#e2e8f0;background:#0b0b0c;padding:3px 7px;border-radius:2px",
    "color:#868e96"
  );
  console.log(
    "%cPoking around? The board renders from src/domains/map, player areas from src/domains/player, and the whole visual system is documented in DESIGN.md.",
    "color:#6b7280"
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
