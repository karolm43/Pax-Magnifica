import { useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { IconMinimize, IconSwords } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useBattle, useBoardEditor, type BattleView } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import { getColorAlias, resolvePrimaryRgb } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import {
  absorbed,
  autoMarks,
  expandShips,
  MARK_WEIGHT,
  nextMark,
  planFromMarks,
  type Mark,
  type ShipEntity,
} from "./battleAssign";
import { useDyingShips, useMaxHp, useVolley, type Volley } from "./useBattleFx";
import { BattleFleet } from "./BattleFleet";
import { BattleCenter } from "./BattleCenter";
import styles from "./BattleOverlay.module.css";

/** Warstwa pocisków salwy: tory od strzelającej strony do przeciwnej, rozbłysk przy trafieniu. */
function VolleyLayer({ volley }: { volley: Volley | null }) {
  if (!volley) return null;
  return (
    <div className={styles.volleyLayer} aria-hidden="true" key={volley.id}>
      {volley.bolts.map((bolt) => (
        <span
          key={bolt.id}
          className={styles.bolt}
          data-from={bolt.from}
          data-hit={bolt.hit || undefined}
          data-afb={volley.phase === "AFB" || undefined}
          style={
            {
              "--lane": `${bolt.lane}%`,
              "--delay": `${bolt.delayMs}ms`,
            } as CSSProperties
          }
        />
      ))}
      {volley.bolts
        .filter((bolt) => bolt.hit)
        .map((bolt) => (
          <span
            key={`${bolt.id}-impact`}
            className={styles.impact}
            data-from={bolt.from}
            style={
              {
                "--lane": `${bolt.lane}%`,
                "--delay": `${bolt.delayMs + 430}ms`,
              } as CSSProperties
            }
          />
        ))}
    </div>
  );
}

function usePlayers() {
  const gameData = useGameData();
  return (key: string) => {
    const player = gameData?.playerData?.find((p) => p.faction === key);
    const rgb = player?.color ? resolvePrimaryRgb(player.color) : undefined;
    return {
      name: player ? getPlayerFactionDisplayName(player) : key,
      colorAlias: getColorAlias(player?.color),
      // Składowe ODDZIELONE SPACJAMI — CSS używa `rgb(var(--x) / alfa)`, a ta składnia
      // nie akceptuje przecinków (cała deklaracja tła byłaby odrzucona → przezroczyste okno).
      rgb: rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "148 163 184",
    };
  };
}

function Battlefield({ view }: { view: BattleView }) {
  const gameData = useGameData();
  const players = usePlayers();
  const setHidden = useAppStore((s) => s.setBattleHidden);
  // Okno przykrywa panel komunikatów mapy — odrzucenia (422) pokazujemy tutaj.
  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);
  const { battleAfb, battleRoll, battleAssign, battleClose } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const attacker = view.attacker!;
  const defender = view.defender!;
  const attackerShips = expandShips(attacker);
  const defenderShips = expandShips(defender);
  const attackerViews = useDyingShips(attackerShips);
  const defenderViews = useDyingShips(defenderShips);
  const attackerMax = useMaxHp(`${view.position}-${attacker.faction}`, attacker.hp);
  const defenderMax = useMaxHp(`${view.position}-${defender.faction}`, defender.hp);
  const volley = useVolley(view);

  // Znaczniki strat są ważne tylko dla bieżącego przypisania (runda + gracz + salwa).
  const assignKey = `${view.round}:${view.assigning ?? ""}:${view.log.length}`;
  const [marksState, setMarksState] = useState<{ key: string; marks: Record<string, Mark> }>(
    { key: "", marks: {} },
  );
  const marks = marksState.key === assignKey ? marksState.marks : {};
  const assigningShips =
    view.assigning === attacker.faction
      ? attackerShips
      : view.assigning === defender.faction
        ? defenderShips
        : [];
  const required = view.assigning ? (view.required[view.assigning] ?? 0) : 0;
  const covered = absorbed(marks);

  const setMarks = (next: Record<string, Mark>) => setMarksState({ key: assignKey, marks: next });

  const toggle = (ship: ShipEntity) => {
    const current = marks[ship.id];
    let candidate = nextMark(ship, current);
    const others = covered - (current ? MARK_WEIGHT[current] : 0);
    // Nie pozwól pokryć więcej trafień, niż trzeba — wtedy znacznik znika.
    while (candidate && others + MARK_WEIGHT[candidate] > required) {
      candidate = nextMark(ship, candidate);
    }
    const next = { ...marks };
    if (candidate) next[ship.id] = candidate;
    else delete next[ship.id];
    setMarks(next);
  };

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód (422) pokazuje panel komunikatów (post() → notice).
    } finally {
      setBusy(false);
    }
  };

  const a = players(attacker.faction);
  const d = players(defender.faction);
  const nameOf = (key: string) => players(key).name;
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName = tile ? (getTileById(tile.systemId)?.name ?? view.position) : view.position;
  const where =
    view.kind === "ground" ? `${view.planet ?? ""} · ${systemName ?? ""}` : (systemName ?? "");

  return (
    <div
      className={styles.overlay}
      data-kind={view.kind ?? undefined}
      data-nebula={view.nebula || undefined}
      role="dialog"
      aria-modal="true"
      aria-label={`${view.kind === "ground" ? "Ground" : "Space"} combat: ${a.name} vs ${d.name}`}
      style={{ "--left-rgb": a.rgb, "--right-rgb": d.rgb } as CSSProperties}
    >
      <div className={styles.stars} aria-hidden="true" />
      <header className={styles.topBar}>
        <span className={styles.topTitle}>
          <IconSwords size={18} aria-hidden="true" />
          {view.kind === "ground" ? "Ground Combat" : "Space Combat"}
          <small>
            {view.position} · {where}
          </small>
        </span>
        <span className={styles.versus}>
          <b style={{ color: `rgb(${a.rgb})` }}>{a.name}</b>
          <i>vs</i>
          <b style={{ color: `rgb(${d.rgb})` }}>{d.name}</b>
        </span>
        <button
          type="button"
          className={styles.hideBtn}
          onClick={() => setHidden(true)}
          title="Hide the battle and look at the map (the combat keeps going)"
        >
          <IconMinimize size={15} aria-hidden="true" /> Hide
        </button>
      </header>

      {notice && (
        <div className={styles.notice} data-kind={notice.kind} role="alert">
          <span>{notice.text}</span>
          <button type="button" onClick={clearNotice} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <div className={styles.field}>
        <BattleFleet
          side={attacker}
          views={attackerViews}
          align="left"
          name={a.name}
          colorAlias={a.colorAlias}
          maxHp={attackerMax}
          isWinner={view.winner === attacker.faction}
          assigning={view.step === "ASSIGN" && view.assigning === attacker.faction}
          marks={view.assigning === attacker.faction ? marks : {}}
          onToggle={toggle}
        />
        <BattleCenter
          view={view}
          nameOf={nameOf}
          busy={busy}
          absorbed={covered}
          onAfb={() => void run(battleAfb)}
          onRoll={() => void run(battleRoll)}
          onAuto={() => setMarks(autoMarks(assigningShips, required))}
          onClearMarks={() => setMarks({})}
          onConfirmAssign={() =>
            view.assigning &&
            void run(() =>
              battleAssign(view.assigning!, planFromMarks(assigningShips, marks)),
            )
          }
          onClose={() => void run(battleClose)}
        />
        <BattleFleet
          side={defender}
          views={defenderViews}
          align="right"
          name={d.name}
          colorAlias={d.colorAlias}
          maxHp={defenderMax}
          isWinner={view.winner === defender.faction}
          assigning={view.step === "ASSIGN" && view.assigning === defender.faction}
          marks={view.assigning === defender.faction ? marks : {}}
          onToggle={toggle}
        />
        <VolleyLayer volley={volley} />
      </div>
    </div>
  );
}

/**
 * Okno POLA BITWY (RULES.md 39) — pełnoekranowe, pojawia się samo, gdy trwa walka
 * (``gameState.activeCombat``). Floty wlatują z lewej (atakujący) i prawej (obrońca),
 * widać życie stron, wartości bojowe, salwy z animacją pocisków i wynik. Rzuty i straty
 * rozstrzyga silnik; okno tylko prowadzi i animuje. „Hide" chowa je na chwilę.
 */
export function BattleOverlay() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const hidden = useAppStore((s) => s.battleHidden);
  const setHidden = useAppStore((s) => s.setBattleHidden);
  const inCombat = gameState?.activeCombat != null;
  const { data: view } = useBattle(inCombat);

  if (!inCombat || !view?.active || !view.attacker || !view.defender) return null;

  if (hidden) {
    return createPortal(
      <button type="button" className={styles.returnPill} onClick={() => setHidden(false)}>
        <IconSwords size={16} aria-hidden="true" />
        Battle in progress — return
      </button>,
      document.body,
    );
  }
  return createPortal(<Battlefield view={view} />, document.body);
}

export default BattleOverlay;
