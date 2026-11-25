import { UnitStack } from "@/domains/map/components/UnitStack";
import { useGameData, useMapReplay } from "@/state/useGameContext";
import { useResolveColorAlias } from "../hooks/useResolveColorAlias";
import classes from "./MapUnitTransitionLayer.module.css";
import { CommandCounter } from "@/domains/map/components/CommandCounter";
import { ControlToken } from "@/shared/ui/ControlToken";
import { useEffect, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import type { FlightEffectKind } from "@/entities/replay/flightPath";

const TOKEN_KIND_CLASS = {
  activation: classes.commandTokenPlacement,
  added: classes.commandTokenAdded,
  removed: classes.commandTokenRemoved,
};

function tokenTimingStyle(token: {
  x: number;
  y: number;
  delayMs: number;
  durationMs: number;
}) {
  return {
    left: token.x,
    top: token.y,
    "--command-delay": `${token.delayMs}ms`,
    "--command-duration": `${token.durationMs}ms`,
  } as CSSProperties;
}

const EFFECT_CLASS = {
  wormholeIn: classes.wormholeIn,
  wormholeOut: classes.wormholeOut,
  portalIn: classes.portalIn,
  portalOut: classes.portalOut,
  riftWarp: classes.riftWarp,
  nebulaDamp: classes.nebulaDamp,
  asteroidDust: classes.asteroidDust,
  supernovaFlare: classes.supernovaFlare,
} satisfies Record<FlightEffectKind, string>;

function isTyping(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(target.tagName))
  );
}

/**
 * A replay never blocks play: Esc or Space (outside text fields and buttons) or the "Skip"
 * pill ends it at once and the map shows its final state.
 */
function useSkipShortcut(active: boolean, skip: (() => void) | undefined) {
  useEffect(() => {
    if (!active || !skip) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || isTyping(event.target)) return;
      if (event.key !== "Escape" && event.key !== " ") return;
      event.preventDefault();
      skip();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, skip]);
}

export function MapUnitTransitionLayer() {
  const mapReplay = useMapReplay();
  const { transitions, lasers, flightEffects, skip } = mapReplay;
  const lawsInPlay = useGameData()?.lawsInPlay;
  const resolveColorAlias = useResolveColorAlias();
  const hasContent =
    transitions.length > 0 ||
    lasers.length > 0 ||
    flightEffects.length > 0 ||
    mapReplay.commandTokens.length > 0 ||
    mapReplay.controlTokens.length > 0;
  useSkipShortcut(mapReplay.active && hasContent, skip);

  if (!mapReplay.active || !hasContent) return null;

  return (
    <div className={classes.layer} aria-hidden="true">
      {skip &&
        createPortal(
          <button
            type="button"
            className={classes.skip}
            onClick={skip}
            aria-label="Skip movement animation"
          >
            Skip ⏭
          </button>,
          document.body,
        )}
      {flightEffects.map((effect, index) => (
        <span
          key={`${mapReplay.key}-effect-${index}`}
          className={`${classes.flightEffect} ${EFFECT_CLASS[effect.kind]}`}
          style={
            {
              left: effect.x,
              top: effect.y,
              "--effect-delay": `${effect.delayMs}ms`,
              "--effect-duration": `${effect.durationMs}ms`,
            } as CSSProperties
          }
        />
      ))}
      {mapReplay.commandTokens.map((token) => {
        const colorAlias = resolveColorAlias(token.faction);
        return (
          <div
            key={`${mapReplay.key}-command-${token.position}-${token.faction}-${token.index}`}
            className={TOKEN_KIND_CLASS[token.kind]}
            style={tokenTimingStyle(token)}
          >
            <CommandCounter colorAlias={colorAlias} faction={token.faction} />
          </div>
        );
      })}
      {mapReplay.controlTokens.map((token) => {
        const colorAlias = resolveColorAlias(token.faction);
        return (
          <div
            key={`${mapReplay.key}-control-${token.position}-${token.planet}-${token.faction}-${token.kind}`}
            className={TOKEN_KIND_CLASS[token.kind]}
            style={tokenTimingStyle(token)}
          >
            <ControlToken
              colorAlias={colorAlias}
              faction={token.faction}
              style={{ transform: "translate(-50%, -50%)" }}
            />
          </div>
        );
      })}
      {lasers.map((laser, index) => {
        const deltaX = laser.toX - laser.fromX;
        const deltaY = laser.toY - laser.fromY;
        const distance = Math.hypot(deltaX, deltaY);
        const angle = (Math.atan2(deltaY, deltaX) * 180) / Math.PI;
        return (
          <span
            key={`${mapReplay.key}-laser-${index}`}
            className={classes.laserPath}
            style={
              {
                left: laser.fromX,
                top: laser.fromY,
                width: distance,
                transform: `rotate(${angle}deg)`,
                "--laser-distance": `${distance}px`,
                "--laser-delay": `${laser.delayMs}ms`,
                "--laser-duration": `${laser.durationMs}ms`,
                "--laser-color":
                  laser.color === "attacker" ? "#67e8f9" : "#fb7185",
              } as CSSProperties
            }
          >
            <span className={classes.laserBolt} />
          </span>
        );
      })}
      {transitions.map((transition, index) => {
        const { stack } = transition;
        const colorAlias = resolveColorAlias(stack.faction);

        return (
          <UnitStack
            key={`${mapReplay.key}-${transition.kind}-${stack.faction}-${stack.entityId}-${index}`}
            stack={stack}
            stackKey={`map-transition-${index}`}
            colorAlias={colorAlias}
            lawsInPlay={lawsInPlay}
            mapTransition={transition}
          />
        );
      })}
    </div>
  );
}
