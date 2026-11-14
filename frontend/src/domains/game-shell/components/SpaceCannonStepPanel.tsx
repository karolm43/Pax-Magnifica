import { useEffect, useRef, useState } from "react";
import { HoldRollButton } from "@/domains/dice/HoldRollButton";
import { soloHold, useDiceStage } from "@/domains/dice/diceStage";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import {
  IconBolt,
  IconEye,
  IconEyeOff,
  IconHandStop,
} from "@tabler/icons-react";
import {
  useBoardEditor,
  useSpaceCannon,
  type SpaceCannonSide,
} from "@/api/useBoardEditor";
import { useSettingsStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { Switch } from "@/ds";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import { Unit } from "@/shared/ui/Unit";
import {
  AssignHits,
  DiceRolls,
  SpaceCannonLog,
  usePlayerLookup,
  zoneLabel,
} from "./SpaceCannonParts";
import styles from "./SpaceCannonStepPanel.module.css";
import { PlayerTag } from "@/shared/ui/PlayerTag";

type Lookup = ReturnType<typeof usePlayerLookup>;

/** Sekcja karty tury z podpisem (Shooters / Modifiers / Target). */
function Block({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.block}>
      <h4 className={styles.blockTitle}>{title}</h4>
      {children}
    </div>
  );
}

/** Czy gracz ma technologie istotne dla Space Cannon (żeby nie rysować pustej sekcji). */
function hasTechs(
  gameData: ReturnType<typeof useGameData>,
  faction: string,
): boolean {
  const p = gameData?.playerData?.find((x) => x.faction === faction);
  return (p?.techEffects ?? []).some((t) => t.contexts.includes("spaceCannon"));
}

/**
 * Karta tury bieżącego strzelca: jego jednostki z Space Cannon (próg, kości, zasięg),
 * wybór celu (aktywny gracz wybiera; nieaktywny celuje w aktywnego) oraz Fire / Pass.
 * Stan wyboru celu jest lokalny — rodzic montuje kartę z ``key`` bieżącego gracza.
 */
function TurnCard({
  side,
  lookup,
  busy,
  onFire,
  onPass,
}: {
  side: SpaceCannonSide;
  lookup: Lookup;
  busy: boolean;
  onFire: (target: string, plasmaUnit: string | null) => void;
  onPass: () => void;
}) {
  const gameData = useGameData();
  const lookRgb = usePlayerLook();
  const me = { ...lookup(side.faction), rgb: lookRgb(side.faction).rgb };
  const [target, setTarget] = useState<string | null>(
    side.targets.length === 1 ? side.targets[0] : null,
  );
  // Plasma Scoring ("may"): wybór jednostki z dodatkową kością. Domyślnie najcelniejsza grupa,
  // ale gracz może wskazać inną albo zrezygnować.
  const plasmaGroups = side.shooters.filter((s) => s.plasmaDice > 0);
  const bestPlasma = [...plasmaGroups].sort((a, b) => a.hitsOn - b.hitsOn)[0];
  const [plasma, setPlasma] = useState<string | null>(bestPlasma?.key ?? null);
  const plasmaDice = plasma
    ? (plasmaGroups.find((s) => s.key === plasma)?.plasmaDice ?? 0)
    : 0;

  const shooterTechs = hasTechs(gameData, side.faction);
  const totalRolled = side.totalDice + plasmaDice;

  return (
    <section className={styles.turn} aria-label={`${me.name} may fire`}>
      <header className={styles.turnHead}>
        <CircularFactionIcon faction={side.faction} size={26} />
        <span className={styles.turnWho}>
          <small>Now firing</small>
          <b>{me.name}</b>
        </span>
      </header>

      <div className={styles.stats}>
        <div className={styles.stat}>
          <b>{totalRolled}</b>
          <small>dice</small>
        </div>
        <div className={styles.stat}>
          <b>~{side.expectedHits}</b>
          <small>expected hits</small>
        </div>
        <div className={styles.stat}>
          <b>{side.targets.length}</b>
          <small>{side.targets.length === 1 ? "target" : "targets"}</small>
        </div>
      </div>

      <Block title="Shooters">
        <div className={styles.shooters}>
          <div className={styles.shooterHead} aria-hidden="true">
            <span>Unit</span>
            <span>Hits on</span>
            <span>Dice</span>
          </div>
          {side.shooters.map((s) => (
            <div
              key={`${s.baseType}-${s.position}-${s.zone}`}
              className={styles.shooterRow}
            >
              <div className={styles.icon}>
                <Unit
                  unitType={s.asyncId}
                  colorAlias={me.colorAlias}
                  faction={side.faction}
                  scaleSprite
                />
              </div>
              <span className={styles.shooterName}>
                <b>{s.count}×</b> {s.name}
                {s.remote && (
                  <span
                    className={styles.badge}
                    title="Deep Space Cannon: fires from an adjacent system"
                  >
                    from {s.position}
                  </span>
                )}
              </span>
              <span className={styles.chip} title="Each die hits on this result or higher">
                {s.hitsOn}+
              </span>
              <span className={styles.chip} title="Total dice rolled by this group">
                {s.count * s.dicePerUnit}
              </span>
            </div>
          ))}
        </div>
      </Block>

      {(shooterTechs || plasmaGroups.length > 0) && (
        <Block title="Your modifiers">
          {shooterTechs && (
            <ActiveTechs context="spaceCannon" faction={side.faction} />
          )}
          {plasmaGroups.length > 0 && (
            <div
              className={styles.plasma}
              role="radiogroup"
              aria-label="Plasma Scoring"
            >
              <small>
                Plasma Scoring: one unit may roll 1 extra die. Pick which one.
              </small>
              {plasmaGroups.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  role="radio"
                  aria-checked={plasma === s.key}
                  className={styles.plasmaOption}
                  data-active={plasma === s.key || undefined}
                  onClick={() => setPlasma(s.key)}
                >
                  <span>
                    {s.name} <small>({s.hitsOn}+)</small>
                  </span>
                  <small>
                    {s.remote ? `from ${s.position}` : zoneLabel(s)} · +1 die
                  </small>
                </button>
              ))}
              <button
                type="button"
                role="radio"
                aria-checked={plasma === null}
                className={styles.plasmaOption}
                data-active={plasma === null || undefined}
                onClick={() => setPlasma(null)}
              >
                <span>No extra die</span>
              </button>
            </div>
          )}
        </Block>
      )}

      <Block title={side.targets.length > 1 ? "Choose target" : "Target"}>
        <div
          className={styles.targets}
          role={side.targets.length > 1 ? "radiogroup" : undefined}
          aria-label="Choose target"
        >
          {side.targets.map((key) => (
            <div
              key={key}
              role={side.targets.length > 1 ? "radio" : undefined}
              aria-checked={side.targets.length > 1 ? target === key : undefined}
              tabIndex={side.targets.length > 1 ? 0 : undefined}
              className={styles.target}
              data-active={target === key || undefined}
              data-single={side.targets.length === 1 || undefined}
              onClick={() => setTarget(key)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setTarget(key);
                }
              }}
            >
              <span className={styles.targetHead}>
                <CircularFactionIcon faction={key} size={18} />
                <b>{lookup(key).name}</b>
                {side.targets.length === 1 && <small>active player</small>}
              </span>
              <ActiveTechs
                context="spaceCannon"
                faction={key}
                className={styles.targetTechs}
              />
            </div>
          ))}
        </div>
      </Block>

      <div className={styles.actions}>
        <HoldRollButton
          className={styles.fire}
          disabled={busy || target === null}
          onFire={() => target !== null && onFire(target, plasma)}
          onHold={soloHold(side.totalDice + plasmaDice, me.rgb)}
          hint={false}
          title={
            target === null
              ? "Pick a target first"
              : "Roll Space Cannon dice (hold to shake the dice, release to throw)"
          }
        >
          <IconBolt size={15} aria-hidden="true" /> Fire
        </HoldRollButton>
        <button
          type="button"
          className={styles.pass}
          disabled={busy}
          onClick={onPass}
        >
          <IconHandStop size={15} aria-hidden="true" /> Don't fire
        </button>
      </div>
    </section>
  );
}

/**
 * Krok SPACE CANNON akcji taktycznej — panel Offense (RULES.md 38). Prowadzi okno
 * czasowe: kolejka graczy (od aktywnego, zgodnie z zegarem), karta bieżącego strzelca,
 * wynik rzutu z kośćmi, przypisanie strat przez gracza-cel i dziennik. Strzelać może
 * KAŻDY gracz z Space Cannon w zasięgu, nie tylko aktywny; zasięg (Deep Space Cannon,
 * PDS II) wynika z danych i jest widoczny w soczewce mapy „Space Cannon range".
 */
export function SpaceCannonStepPanel() {
  const { data: panel } = useSpaceCannon(true);
  const gameData = useGameData();
  // Graviton Laser System (RULES.md 57): gracz ŚWIADOMIE wyczerpuje go przed strzałem.
  const [useGls, setUseGls] = useState(false);
  const { spaceCannonFire, spaceCannonPass, spaceCannonAssign } =
    useBoardEditor();
  const lookup = usePlayerLookup();
  const showRange = useSettingsStore((s) => s.settings.showPDSLayer);
  const toggleRange = useSettingsStore((s) => s.handlers.togglePdsMode);
  const [busy, setBusy] = useState(false);
  const look = usePlayerLook();
  const throwDice = useDiceStage((s) => s.throwDice);

  // Nowy rzut: fizyczne kości na wspólnej scenie, a wynik w panelu odsłania się, gdy leżą.
  const pendingNow = panel?.pending ?? null;
  const rollKey = pendingNow
    ? `${pendingNow.roller}>${pendingNow.target}:${pendingNow.hits}:${panel?.log.length ?? 0}`
    : "";
  const seenKey = useRef<string | undefined>(undefined);
  const [revealed, setRevealed] = useState("");
  const revealTimer = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (!panel) return;
    if (seenKey.current === undefined) {
      seenKey.current = rollKey; // rzut sprzed otwarcia panelu nie jest nowością
      setRevealed(rollKey);
      return;
    }
    if (rollKey === seenKey.current) return;
    seenKey.current = rollKey;
    if (!pendingNow) return;
    const { pauseMs } = throwDice({
      left: pendingNow.rolls.map((r) => ({
        dice: r.dice,
        // Antimass Deflectors celu (-1 do wyniku) widać też na scenie kości.
        modifier: r.modifier ?? 0,
        hitsOn: r.hitsOn,
      })),
      leftRgb: look(pendingNow.roller).rgb,
    });
    window.clearTimeout(revealTimer.current);
    revealTimer.current = window.setTimeout(
      () => setRevealed(rollKey),
      pauseMs,
    );
  }, [panel, rollKey, pendingNow, look, throwDice]);
  useEffect(() => () => window.clearTimeout(revealTimer.current), []);
  const rolling = rollKey !== "" && revealed !== rollKey;

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód odrzucenia (422) pokazał już panel komunikatów (post() → notice).
    } finally {
      setBusy(false);
    }
  };

  if (!panel) return <span className={styles.note}>Loading Space Cannon…</span>;

  const nameOf = (key: string) => lookup(key).name;
  // Strzelec i cel z logo frakcji i kolorem gracza (``PlayerTag``), nie sama nazwa.
  const factionTag = (faction: string, name: string) => {
    const player = gameData?.playerData?.find((p) => p.faction === faction);
    return player ? (
      <PlayerTag playerId={player.discordId} size={16} known={{ name }} />
    ) : (
      <b>{name}</b>
    );
  };
  const current = panel.sides.find((s) => s.faction === panel.current);
  const shooter = gameData?.playerData?.find(
    (p) => p.faction === current?.faction,
  );
  const glsReady =
    (shooter?.techs ?? []).includes("gls") &&
    !(shooter?.exhaustedTechs ?? []).includes("gls");
  const pending = panel.pending;
  const pendingKey = pending
    ? `${pending.roller}>${pending.target}:${pending.hits}:${panel.log.length}`
    : "";
  // Trwający rzut jest już w dzienniku (dopisany przy strzale) — nie pokazuj go dwa razy.
  const history = pending ? panel.log.slice(0, -1) : panel.log;

  return (
    <div className={styles.root}>
      <div className={styles.topBar}>
        <span className={styles.title}>Space Cannon Offense</span>
        <button
          type="button"
          className={styles.lens}
          aria-pressed={showRange}
          onClick={toggleRange}
          title="Highlight systems under Space Cannon fire (key P)"
        >
          {showRange ? <IconEyeOff size={13} /> : <IconEye size={13} />}
          Range
        </button>
      </div>

      {!panel.isOpen && !panel.resolved && (
        <p className={styles.note}>
          Nothing can fire here: no Space Cannon units in range, or no one to
          hit. Space Cannon needs units in this system, or PDS II (Deep Space
          Cannon) in an adjacent one.
        </p>
      )}
      {!panel.isOpen && panel.resolved && (
        <p className={styles.done}>
          Space Cannon resolved — continue with Next step.
        </p>
      )}

      {panel.isOpen && (
        <ol className={styles.queue} aria-label="Firing order">
          {panel.queue.map((key) => {
            const state = panel.responded.includes(key)
              ? "done"
              : key === panel.current
                ? "now"
                : "wait";
            return (
              <li key={key} className={styles.queueItem} data-state={state}>
                <CircularFactionIcon faction={key} size={18} />
                <span>{nameOf(key)}</span>
              </li>
            );
          })}
        </ol>
      )}

      {pending ? (
        <div style={{ visibility: rolling ? "hidden" : "visible" }}>
          <header className={styles.shotHead}>
            <span>
              {factionTag(pending.roller, nameOf(pending.roller))} fires on{" "}
              {factionTag(pending.target, nameOf(pending.target))}
            </span>
            <span
              className={styles.hitCount}
              data-hits={pending.hits > 0 || undefined}
            >
              {pending.hits} hit{pending.hits === 1 ? "" : "s"}
            </span>
          </header>
          <span
            className={styles.beam}
            data-hits={pending.hits > 0 || undefined}
          />
          <DiceRolls rolls={pending.rolls} />
          <AssignHits
            key={pendingKey}
            pending={pending}
            ships={panel.targetShips}
            targetName={nameOf(pending.target)}
            colorAlias={lookup(pending.target).colorAlias}
            faction={pending.target}
            busy={busy}
            onConfirm={(plan) =>
              void run(() => spaceCannonAssign(pending.target, plan))
            }
          />
        </div>
      ) : (
        current && (
          <>
            {glsReady && (
              <Switch
                size="xs"
                label="Exhaust Graviton Laser System (hits must go to non-fighter ships)"
                checked={useGls}
                onChange={(event) => setUseGls(event.currentTarget.checked)}
                disabled={busy}
              />
            )}
            <TurnCard
              key={current.faction}
              side={current}
              lookup={lookup}
              busy={busy}
              onFire={(target, plasmaUnit) =>
                void run(async () => {
                  await spaceCannonFire(
                    current.faction,
                    target,
                    glsReady && useGls,
                    plasmaUnit,
                  );
                  setUseGls(false);
                })
              }
              onPass={() => void run(() => spaceCannonPass(current.faction))}
            />
          </>
        )
      )}

      <SpaceCannonLog log={history} nameOf={nameOf} />
    </div>
  );
}
