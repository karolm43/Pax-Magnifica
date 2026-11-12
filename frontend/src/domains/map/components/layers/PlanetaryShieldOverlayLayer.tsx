import { useEffect, useRef, useState } from "react";
import { getPlanetPositionsBySystemId, getPlanetData } from "@/entities/lookup/planets";
import { assetUrl } from "@/shared/assets/resolveAsset";
import styles from "./PlanetaryShieldOverlayLayer.module.css";
import type { Tile } from "@/entities/game/types";
import { isLargeLegendaryPlanet } from "./legendaryPlanetSize";

type Props = {
  systemId: string;
  mapTile: Tile;
};

/** Czas animacji utraty tarczy (zgodny z ``shieldBreak`` w CSS). */
const BREAK_MS = 1600;

/**
 * Tarcza planetarna na planetach (silnik liczy ``planetaryShield``: jednostka z PLANETARY SHIELD,
 * której nikt nie odebrał — np. Arc Secundus). Gdy tarcza znika, ikona migocze, pęka i gaśnie,
 * żeby utrata była widoczna, a nie cicha.
 */
export function PlanetaryShieldOverlayLayer({ systemId, mapTile }: Props) {
  const planetPositions = getPlanetPositionsBySystemId(systemId);
  const shielded = Object.entries(mapTile.planets)
    .filter(([, planet]) => planet.planetaryShield)
    .map(([planetId]) => planetId);
  const key = shielded.join("|");

  // Planety, które właśnie straciły tarczę (animacja do końca, potem znikają z DOM).
  const previous = useRef<Set<string> | null>(null);
  const [breaking, setBreaking] = useState<string[]>([]);
  useEffect(() => {
    const now = new Set(key === "" ? [] : key.split("|"));
    const before = previous.current;
    previous.current = now;
    if (before === null) return; // pierwsze wyrenderowanie: bez animacji
    const lost = [...before].filter((planetId) => !now.has(planetId));
    if (lost.length === 0) return;
    setBreaking((prev) => [...new Set([...prev, ...lost])]);
    const timer = window.setTimeout(
      () => setBreaking((prev) => prev.filter((planetId) => !lost.includes(planetId))),
      BREAK_MS,
    );
    return () => window.clearTimeout(timer);
  }, [key]);

  const icon = (planetId: string, state: "up" | "break") => {
    const position = planetPositions[planetId];
    if (!position) return null;
    const isMecatolRex = planetId === "mr";
    const isLargeLegendary = isLargeLegendaryPlanet(planetId, getPlanetData(planetId));
    const scale = isMecatolRex ? 1.9 : isLargeLegendary ? 1.65 : 0.95;
    return (
      <img
        key={`${systemId}-${planetId}-pshield-${state}`}
        src={assetUrl("/tokens/token_planetaryShield.png")}
        alt={state === "up" ? "Planetary Shield" : "Planetary Shield lost"}
        className={styles.icon}
        data-state={state}
        style={
          {
            position: "absolute",
            left: `${position.x}px`,
            top: `${position.y}px`,
            "--shield-scale": scale,
            transform: `translate(-50%, -50%) scale(${scale})`,
          } as React.CSSProperties
        }
      />
    );
  };

  return (
    <>
      {shielded.map((planetId) => icon(planetId, "up"))}
      {breaking.filter((planetId) => !shielded.includes(planetId)).map((planetId) => icon(planetId, "break"))}
    </>
  );
}
