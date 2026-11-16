import { useCallback, useEffect, useId, useRef } from "react";
import { useAppStore, type MapTargetKind } from "@/state/appStore";

type PickOptions = { hue?: string; selected?: string | null; enabled?: boolean };

/** Stan wyboru okna: czy to ono trzyma teraz mapę i jak ją przejąć. */
export type MapPickHandle = {
  /** Wybór tego okna jest aktywny (jego cele świecą, klik trafia do niego). */
  active: boolean;
  /** Okno ma wpis w rejestrze (są cele i wybór włączony), choć może czekać pod innym. */
  registered: boolean;
  /** Przejmij mapę (np. klik w okno, przycisk „Pick here”). */
  claim: () => void;
};

/**
 * Wybór celu NA MAPIE na czas życia komponentu - systemy (klik w heks) i/lub planety (klik w
 * planetę) naraz. Okno dostaje własny wpis w rejestrze ``appStore.mapPicks`` (``useId``), więc
 * dwa otwarte okna nie kasują sobie wyboru: aktywny jest wpis najnowszy albo przejęty
 * ``claim()``; po zamknięciu okna mapa wraca do poprzedniego. ``onPick`` w refie, żeby nowy
 * callback nie restartował podświetlenia. Brak celów albo ``enabled=false`` = brak wpisu.
 */
export function useMapTargets(
  targets: { systems?: string[]; planets?: string[] },
  onPick: (target: string, kind: MapTargetKind) => void,
  options: PickOptions = {},
): MapPickHandle {
  const owner = useId();
  const put = useAppStore((s) => s.putMapPick);
  const drop = useAppStore((s) => s.dropMapPick);
  const raise = useAppStore((s) => s.raiseMapPick);
  const active = useAppStore((s) => s.mapPicks.at(-1)?.owner === owner);
  const registered = useAppStore((s) => s.mapPicks.some((e) => e.owner === owner));
  const pickRef = useRef(onPick);
  pickRef.current = onPick;
  const systems = targets.systems ?? [];
  const planets = targets.planets ?? [];
  const systemsKey = systems.join("|");
  const planetsKey = planets.join("|");
  const { hue, selected, enabled = true } = options;
  const on = enabled && systems.length + planets.length > 0;

  // Wpis żyje, dopóki wybór włączony; zmiana celów / zaznaczenia aktualizuje go W MIEJSCU
  // (bez przeskakiwania na wierzch - inaczej każdy klik w okno zabierałby mapę sąsiadowi).
  useEffect(() => {
    if (!on) return;
    return () => drop(owner);
  }, [on, owner, drop]);
  useEffect(() => {
    if (!on) return;
    put(owner, {
      systems,
      planets,
      hue,
      selected: selected ?? null,
      onPick: (target, kind) => pickRef.current(target, kind),
    });
    // Listy porównujemy przez klucze (nowa tablica przy każdym renderze).
  },[on, owner, put, systemsKey, planetsKey, hue, selected]);

  const claim = useCallback(() => raise(owner), [raise, owner]);
  return { active, registered, claim };
}

/** Wybór jednego rodzaju celu (system ALBO planeta) - dotychczasowe API okien. */
export function useMapPick(
  kind: MapTargetKind,
  targets: string[],
  onPick: (target: string) => void,
  options: PickOptions = {},
): MapPickHandle {
  return useMapTargets(
    kind === "system" ? { systems: targets } : { planets: targets },
    (target) => onPick(target),
    options,
  );
}
