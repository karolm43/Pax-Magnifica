import { useEffect, useRef } from "react";
import { useAppStore, type MapPick } from "@/state/appStore";

/**
 * Włącza wybór celu NA MAPIE na czas życia komponentu (okna karty strategii).
 *
 * Ustawia ``appStore.mapPick`` (podświetlenie dozwolonych systemów/planet, klik → ``onPick``)
 * i czyści go przy odmontowaniu. ``onPick`` trzymamy w refie, żeby zmiana callbacku nie
 * restartowała podświetlenia. Pusta lista celów = brak wyboru (nic nie podświetlamy).
 */
export function useMapPick(
  kind: MapPick["kind"],
  targets: string[],
  onPick: (target: string) => void,
  options: { hue?: string; selected?: string | null; enabled?: boolean } = {},
) {
  const setMapPick = useAppStore((s) => s.setMapPick);
  const pickRef = useRef(onPick);
  pickRef.current = onPick;
  const key = targets.join("|");
  const { hue, selected, enabled = true } = options;

  useEffect(() => {
    // Wyłączony wybór NIE czyści mapy: mógłby skasować wybór innego komponentu (np. pole z
    // grupami w ``GroupedMapField`` pod wyłączonym ``useFieldMapPick`` rodzica). Własny wybór
    // sprząta funkcja czyszcząca poprzedniego przebiegu (przejście enabled -> disabled).
    if (!enabled || targets.length === 0) return;
    setMapPick({
      kind,
      targets,
      hue,
      selected: selected ?? null,
      onPick: (target) => pickRef.current(target),
    });
    return () => setMapPick(null);
    // ``targets`` porównujemy przez ``key`` (nowa tablica przy każdym renderze).
  }, [kind, key, hue, selected, enabled, setMapPick]);
}
