import { useEffect } from "react";

/**
 * SLOTY HUD — pływające panele gry nie nakładają się w swoich domyślnych miejscach.
 *
 * Panel w DOMYŚLNEJ pozycji (nieprzesunięty przez gracza) publikuje swój wymiar jako
 * zmienną CSS na ``<html>`` (np. ``--hud-left-w`` = prawa krawędź doku akcji taktycznej), a sąsiednie panele
 * liczą z niej swoje miejsce startowe w CSS (ręka zwęża się przy karcie strategii, dok
 * akcji taktycznej kończy się nad panelem stanu gry itd.). Przesunięty panel zwalnia
 * slot (``enabled = false``) — gracz sam wybrał mu miejsce. Odmontowanie usuwa zmienną.
 *
 * Mapa slotów (domyślnie):
 *   lewa góra   — GameStatePanel            → ``--hud-gsp-bottom``
 *   lewy dół    — TacticalActionDock        → ``--hud-left-w`` (prawa krawędź doku)
 *   prawa góra  — centrum decyzji (AbilityPrompts, stała szerokość 420 px)
 *   prawy dół   — panel akcji tury + karta strategii obok → ``--hud-right-w``
 *                 (odległość lewej krawędzi karty od prawej krawędzi okna)
 *   dół środek  — ręka (BottomHandDock)     → ``--hand-dock-clear`` (mierzy sama ręka);
 *                 nad nią StatusPhasePanel, MoveRouteBox i paski nakładek
 */
export type HudMetric =
  | "--hud-gsp-bottom"
  | "--hud-left-w"
  | "--hud-right-w";

/** Wymiar panelu liczony z jego prostokąta i rozmiaru okna. */
export type HudMeasure = (rect: DOMRect) => number;

/** Publikuje wymiar ``el`` jako ``name`` (px), dopóki ``enabled`` i element zamontowany. */
export function useHudMetric(
  el: HTMLElement | null,
  name: HudMetric,
  measure: HudMeasure,
  enabled = true,
): void {
  useEffect(() => {
    const root = document.documentElement;
    if (!el || !enabled) {
      root.style.removeProperty(name);
      return;
    }
    const update = () => {
      const value = Math.max(0, Math.round(measure(el.getBoundingClientRect())));
      root.style.setProperty(name, `${value}px`);
    };
    update();
    window.addEventListener("resize", update);
    const observer =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(update) : null;
    observer?.observe(el);
    return () => {
      window.removeEventListener("resize", update);
      observer?.disconnect();
      root.style.removeProperty(name);
    };
    // `measure` to zwykle funkcja inline - celowo poza zależnościami (liczy z prostokąta).
  }, [el, name, enabled]);
}
