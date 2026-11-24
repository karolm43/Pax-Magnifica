import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import {
  IconMinimize,
  IconSwords,
  IconVolume,
  IconVolumeOff,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import {
  useBattle,
  useBoardEditor,
  type BattleSide,
  type BattleView,
} from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import { getColorAlias, resolvePrimaryRgb } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { ActiveTechs } from "@/shared/ui/ActiveTechs/ActiveTechs";
import {
  assignableShips,
  autoMarks,
  coveredCount,
  isCovered,
  planFromMarks,
  toggleMark,
  type Mark,
  type ShipEntity,
} from "./battleAssign";
import { useDyingShips, useMaxHp, useVolley, } from "./useBattleFx";
import { BattleFleet, resetFleetEntries } from "./BattleFleet";
import {
  INTENT_TTL_MS,
  NO_INTENT,
  useStableShips,
  type ShipIntent,
} from "./shipIdentity";
import { useOfferActions, useOffers, type OfferView } from "@/api/useOffers";
import { buildActionCardParams } from "@/api/useActionCard";
import { lookupUnit } from "@/entities/lookup/units";
import { asyncOfBase } from "@/domains/movement/routeTypes";
import { BattleCenter, type PickNote } from "./BattleCenter";
import {
  canPick,
  complete,
  pickedAs,
  pickValues,
  shipPickSteps,
  togglePick,
  type PickState,
  type ShipPickStep,
} from "./shipPick";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import type { HoldState } from "@/domains/dice/HoldRollButton";
import { DiceTray } from "./DiceTray";
import { DicePool } from "./DicePool";
import { READ_MS, countDice, volleyStartMs } from "./diceRoll";
import { useDiceHold } from "@/domains/dice/useDiceHold";

import {
  isBattleMuted,
  playBattleSound,
  preloadBattleSounds,
  setBattleMuted,
} from "./battleSound";
import styles from "./BattleOverlay.module.css";
import { BATTLE_BACKGROUND } from "./BattleVolley";
import { VolleyLayer } from "./BattleVolley";
import { AssaultCannonLayer } from "./BattleAssaultCannon";

/** Po starcie strzałów: odpowiedź obrońcy (1,5 s) + lot pocisków, zanim pokażemy straty. */
const HOLD_TAIL_MS = 3200;

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

function Battlefield({
  view,
  offersPending,
  reactionLabel,
}: {
  view: BattleView;
  /** W grze czekają decyzje graczy (``pendingOffers``) — sprawdź, czy któraś to „wskaż okręt". */
  offersPending: boolean;
  /** Trwa pauza ochronna (RULES.md 54.10) — etykieta okna; kroki walki czekają. */
  reactionLabel: string | null;
}) {
  const gameData = useGameData();
  const players = usePlayers();
  const setHidden = useAppStore((s) => s.setBattleHidden);
  const {
    battleAfb,
    battleAfbExtraDice,
    battleRoll,
    battleAssign,
    battleClose,
    battleAnnounceRetreat,
    battleRetreat,
  } = useBoardEditor();
  const [busy, setBusy] = useState(false);
  const { data: offers } = useOffers(offersPending);
  // Kto może kliknąć za daną stronę: w sieci tylko ja; tryb lokalny i tryb testowy hosta
  // (bez miejsca) sterują każdym graczem.
  const { data: me } = useNetworkMe();
  const canAct = (playerId: string) =>
    !me?.network || !me.player_id || me.player_id === playerId;
  const offerActions = useOfferActions();
  const [muted, setMuted] = useState(isBattleMuted);
  useEffect(() => preloadBattleSounds(), []);
  const fieldRef = useRef<HTMLDivElement>(null);

  const attacker = view.attacker!;
  const defender = view.defender!;
  // Zamiar gracza (kliknięte egzemplarze) per strona: przy następnej zmianie składu giną /
  // przyjmują Sustain DOKŁADNIE te sztuki, a nie „ostatnie z typu” (silnik zna tylko liczby).
  const intents = useRef<Record<string, ShipIntent>>({});
  const intentOf = (key: string) => {
    const intent = intents.current[key];
    return intent && Date.now() - (intent.at ?? 0) < INTENT_TTL_MS ? intent : NO_INTENT;
  };
  const attackerShips = useStableShips(attacker, intentOf(attacker.faction), () => {
    delete intents.current[attacker.faction];
  });
  const defenderShips = useStableShips(defender, intentOf(defender.faction), () => {
    delete intents.current[defender.faction];
  });
  // Ostatni wykonany odwrót (wpis RETREAT na końcu dziennika) — jego statki ODLATUJĄ.
  const lastEntry = view.log.length > 0 ? view.log[view.log.length - 1] : null;
  const lastRetreat = lastEntry?.phase === "RETREAT" ? lastEntry.retreat : null;
  const leavingOf = (key: string) =>
    lastRetreat && lastRetreat.player === key ? lastRetreat.units : null;
  const attackerViews = useDyingShips(
    attackerShips,
    leavingOf(attacker.faction),
  );
  const defenderViews = useDyingShips(
    defenderShips,
    leavingOf(defender.faction),
  );

  // Dźwięki odwrotów: sygnał przy ogłoszeniu, świst silników przy odlocie.
  const retreatingCount = view.retreating.length;
  useEffect(() => {
    if (retreatingCount > 0) playBattleSound("retreatHorn");
  }, [retreatingCount]);
  const retreatLogKey = lastRetreat
    ? `${view.log.length}:${lastRetreat.player}`
    : null;
  const retreatSide = lastRetreat?.player === attacker.faction ? -0.6 : 0.6;
  useEffect(() => {
    if (retreatLogKey) playBattleSound("retreat", { pan: retreatSide });
  }, [retreatLogKey, retreatSide]);

  const systemLabel = (position: string) => {
    const t = gameData?.tiles?.[position];
    const name = t ? getTileById(t.systemId)?.name : undefined;
    return name ? `${name} (${position})` : position;
  };
  const retreatOf = (key: string) => {
    if (view.retreated[key]) {
      return {
        state: "withdrew" as const,
        to: systemLabel(view.retreated[key]),
      };
    }
    if (view.retreating.includes(key)) {
      return {
        state:
          view.step === "RETREAT"
            ? ("withdrawing" as const)
            : ("announced" as const),
        to: null,
      };
    }
    return null;
  };
  const attackerMax = useMaxHp(
    `${view.position}-${attacker.faction}`,
    attacker.hp,
  );
  const defenderMax = useMaxHp(
    `${view.position}-${defender.faction}`,
    defender.hp,
  );
  const volleys = useVolley(view);
  const volley = volleys[volleys.length - 1] ?? null;
  // Kości toczą się po stole od początku salwy do chwili, gdy wszystkie leżą.
  const [rollingId, setRollingId] = useState<number | null>(null);
  const volleyId = volley?.id ?? null;
  const diceMs = volley?.diceMs ?? 0;
  useEffect(() => {
    if (volleyId === null || diceMs <= 0) return;
    setRollingId(volleyId);
    const t = window.setTimeout(() => setRollingId(null), diceMs);
    return () => window.clearTimeout(t);
  }, [volleyId, diceMs]);
  const rolling = volleyId !== null && rollingId === volleyId;
  // Pula kości: przytrzymanie „Roll" (hold) → puszczenie (await: czekamy na wynik z silnika,
  // kości lecą potem z puli) → zniknięcie, gdy kości są już na stole.
  const [pool, setPool] = useState<{
    phase: "off" | "hold" | "await";
    at: number;
    left: number;
    right: number;
  }>({ phase: "off", at: 0, left: 0, right: 0 });
  const diceOf = (s: BattleSide) =>
    view.step === "AFB"
      ? s.units.reduce(
          (n, u) => n + (u.afbHitsOn !== null ? u.count * u.afbDice : 0),
          0,
        )
      : s.totalDice;
  // ``side`` = strona rzucająca sama (ROLL): w puli tylko jej kości; brak = obie (AFB).
  const onHold = (state: HoldState, side?: string) => {
    if (state === "start") {
      setPool({
        phase: "hold",
        at: 0,
        left: side && side !== attacker.faction ? 0 : diceOf(attacker),
        right: side && side !== defender.faction ? 0 : diceOf(defender),
      });
    } else if (state === "fire") {
      setPool((p) => ({ ...p, phase: "await", at: Date.now() }));
    } else {
      setPool((p) => ({ ...p, phase: "off" }));
    }
  };
  useEffect(() => {
    if (pool.phase !== "await") return;
    const t = window.setTimeout(
      () => setPool((p) => (p.phase === "await" ? { ...p, phase: "off" } : p)),
      3000,
    );
    return () => window.clearTimeout(t);
  }, [pool.phase]);
  const fromPoolOf = (v: { id: number }) =>
    pool.at > 0 && v.id >= pool.at && v.id - pool.at < 4000;
  const volleyFromPool = volley !== null && fromPoolOf(volley);
  const showPool =
    pool.phase === "hold" || (pool.phase === "await" && !volleyFromPool);
  // Walka dopiero się zaczyna (flota jeszcze wlatuje), a gracz już rzucił: pomiń wlot, żeby
  // statki zostały na polu, zamiast przemontować się i wlecieć drugi raz.
  const skipEntry = view.log.length > 0 || view.step === "ASSIGN";

  // Znaczniki strat są ważne tylko dla bieżącego przypisania (runda + gracz + salwa).
  const assignKey = `${view.round}:${view.assigning ?? ""}:${view.log.length}:${view.step}`;
  const [marksState, setMarksState] = useState<{
    key: string;
    marks: Record<string, Mark>;
  }>({ key: "", marks: {} });
  const assigningSide =
    view.assigning === attacker.faction
      ? attacker
      : view.assigning === defender.faction
        ? defender
        : null;
  const assigningShips =
    assigningSide === attacker
      ? attackerShips
      : assigningSide === defender
        ? defenderShips
        : [];
  const required = view.assigning ? (view.required[view.assigning] ?? 0) : 0;
  // Non-Euclidean Shielding: tarcza anuluje 2 trafienia (wartość z silnika).
  const cancels = assigningSide?.sustainCancels ?? 1;
  // Wymuszony cel (Devotion: statek wskazany przez Yin; Impulse Core: nie-myśliwce) - klikalne
  // tylko te okręty; gdy cel wskazał przeciwnik, znacznik stoi już na wskazanym statku.
  const hitTarget = view.assigning ? view.hitTargets?.[view.assigning] : undefined;
  const allowedShips = assignableShips(assigningShips, hitTarget, required);
  const allowedIds = new Set(allowedShips.map((s) => s.id));
  const presetMarks = hitTarget?.chooser
    ? autoMarks(allowedShips, required, cancels)
    : {};
  const marks = marksState.key === assignKey ? marksState.marks : presetMarks;
  const covered = coveredCount(marks, required, cancels);
  const ready = view.assigning !== null && isCovered(marks, required, cancels);

  const setMarks = (next: Record<string, Mark>) =>
    setMarksState({ key: assignKey, marks: next });

  // Nie pozwól pokryć więcej trafień, niż trzeba — wtedy znacznik znika.
  const toggle = (ship: ShipEntity) => {
    if (!allowedIds.has(ship.id)) return;
    setMarks(toggleMark(marks, ship, required, cancels));
  };
  const targetNote = (() => {
    if (!hitTarget || !assigningSide) return null;
    const names = hitTarget.types
      .map((t) => assigningSide.units.find((u) => u.baseType === t)?.name ?? t)
      .join(", ");
    const hits = hitTarget.count === 1 ? "the hit" : `${hitTarget.count} hits`;
    const state =
      hitTarget.damaged === true
        ? "damaged "
        : hitTarget.damaged === false
          ? "undamaged "
          : "";
    if (hitTarget.chooser) {
      return `${hitTarget.label}: ${players(hitTarget.chooser).name} assigned ${hits} to the ${state}${names}. Only that ship's Sustain Damage can cancel it.`;
    }
    return `${hitTarget.label}: assign ${hits} to ${names} if able.`;
  })();

  // Decyzje „wskaż jednostkę" (Assault Cannon, Duranium Armor, Devotion, Viscount Unlenn,
  // Evelyn DeLouis, Ambush…): jednostki z bieżącego pola decyzji są klikalne dla DECYDUJĄCEGO
  // gracza. Klik zaznacza (ponowny klik odznacza), decyzję zatwierdza „Confirm” w panelu
  // środkowym - przypadkowy klik niczego nie zużywa.
  const [pickStates, setPickStates] = useState<Record<string, PickState>>({});
  const forgetPick = (offerId: string) =>
    setPickStates((prev) => {
      const next = { ...prev };
      delete next[offerId];
      return next;
    });
  const picks = offersPending
    ? shipPickSteps(offers, [attacker.playerId, defender.playerId], pickStates)
    : new Map<string, ShipPickStep>();
  const pickFor = (side: BattleSide) => {
    const step = picks.get(side.playerId);
    if (!step || view.resolving || !canAct(step.offer.player_id)) return null;
    const { offer, state } = step;
    return {
      can: (ship: ShipEntity) => canPick(offer, state, ship, side.playerId),
      picked: (ship: ShipEntity) => pickedAs(offer, state, ship) !== null,
      label: `${offer.name} — ${step.input?.label ?? "selected"}`,
      onPick: (ship: ShipEntity) =>
        setPickStates((prev) => ({
          ...prev,
          [offer.id]: togglePick(offer, prev[offer.id] ?? {}, ship, side.playerId),
        })),
    };
  };
  const confirmPick = (offer: OfferView, state: PickState) => {
    // Wskazane egzemplarze (np. ofiara Assault Cannon) zmieniają się pierwsze — po obu stronach.
    const picked = new Set(Object.values(state).flatMap((byShip) => Object.keys(byShip)));
    for (const side of [attacker, defender]) {
      intents.current[side.faction] = { ...NO_INTENT, prefer: picked, at: Date.now() };
    }
    const { params } = buildActionCardParams(offer.inputs, pickValues(offer, state));
    void run(async () => {
      await offerActions.accept(offer.player_id, offer.id, params);
      forgetPick(offer.id);
    });
  };
  const skipPick = (offer: OfferView) =>
    void run(async () => {
      await offerActions.decline(offer.player_id, offer.id);
      forgetPick(offer.id);
    });
  // Jedna notka na decyzję (decyzja z jednostkami obu stron jest pod oboma właścicielami).
  const pickSteps = [...new Set(picks.values())];
  const pickNotes: PickNote[] = pickSteps.map((step) => {
    const { offer, input, state } = step;
    const decider = [attacker, defender].find(
      (s) => s.playerId === offer.player_id,
    );
    const chosen = offer.inputs.flatMap((field) =>
      Object.values(state[field.key] ?? {}).map((id) =>
        field.kind === "choice" || field.kind === "multi"
          ? (field.options.find((o) => o.id === id)?.label ?? id)
          : id,
      ),
    );
    const owners = input
      ? new Set(input.options.map((o) => o.meta?.player))
      : new Set<unknown>();
    const mode: PickNote["mode"] = !canAct(offer.player_id)
      ? "waiting"
      : me?.player_id === offer.player_id
        ? "you"
        : "control";
    return {
      key: offer.id,
      title: offer.name,
      who: decider ? players(decider.faction).name : offer.player_id,
      label: input?.label ?? null,
      whose:
        owners.size > 1 ? "any" : owners.has(offer.player_id) ? "own" : "enemy",
      many: input?.kind === "multi" ? input.max : 1,
      chosen,
      mode,
      onConfirm: complete(offer, state) ? () => confirmPick(offer, state) : undefined,
      onClear: chosen.length > 0 ? () => forgetPick(offer.id) : undefined,
      onSkip: offer.mandatory ? undefined : () => skipPick(offer),
    };
  });

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
  const systemName = tile
    ? (getTileById(tile.systemId)?.name ?? view.position)
    : view.position;
  const where =
    view.kind === "ground"
      ? `${view.planet ?? ""} · ${systemName ?? ""}`
      : (systemName ?? "");

  return (
    <div
      className={styles.overlay}
      // Okno pełnoekranowe: dok ręki zwija się do paska, a okno rezerwuje pod nim miejsce.
      data-fullscreen-overlay=""
      data-kind={view.kind ?? undefined}
      data-nebula={view.nebula || undefined}
      role="dialog"
      aria-modal="true"
      aria-label={`${view.kind === "ground" ? "Ground" : "Space"} combat: ${a.name} vs ${d.name}`}
      style={{ "--left-rgb": a.rgb, "--right-rgb": d.rgb } as CSSProperties}
    >
      {/* Miejsce na grafikę tła (assets/extra/battle_background.jpg / battle_ground.jpg)
          + przyciemnienie dla czytelności. Bez pliku zostaje ciemne tło z gwiazdami. */}
      <div
        className={styles.backdrop}
        style={{
          backgroundImage: `url("${BATTLE_BACKGROUND[view.kind === "ground" ? "ground" : "space"]}")`,
        }}
        aria-hidden="true"
      />
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
          <b
            className={styles.vsName}
            style={{ "--c": a.rgb } as CSSProperties}
          >
            <span className={styles.vsDot} />
            {a.name}
          </b>
          <i>vs</i>
          <b
            className={styles.vsName}
            style={{ "--c": d.rgb } as CSSProperties}
          >
            <span className={styles.vsDot} />
            {d.name}
          </b>
        </span>
        <span className={styles.topActions}>
          <button
            type="button"
            className={styles.hideBtn}
            data-sound
            onClick={() => {
              setBattleMuted(!muted);
              setMuted(!muted);
            }}
            title={
              muted ? "Sound off — click to enable" : "Sound on — click to mute"
            }
            aria-pressed={!muted}
          >
            {muted ? (
              <IconVolumeOff size={15} aria-hidden="true" />
            ) : (
              <IconVolume size={15} aria-hidden="true" />
            )}
            {muted ? "Muted" : "Sound"}
          </button>
          <button
            type="button"
            className={styles.hideBtn}
            onClick={() => setHidden(true)}
            title="Hide the battle and look at the map (the combat keeps going)"
          >
            <IconMinimize size={15} aria-hidden="true" /> Hide
          </button>
        </span>
      </header>

      {/* Technologie obu stron działające w walce (Assault Cannon, Duranium Armor, Magen...). */}
      <div className={styles.techBar}>
        <ActiveTechs context="combat" faction={attacker.faction} label={a.name} />
        <ActiveTechs context="combat" faction={defender.faction} label={d.name} />
      </div>

      <div
        className={styles.field}
        ref={fieldRef}
        data-volley={volley ? volley.id : undefined}
        data-hits={volley?.bolts.some((b) => b.hit) || undefined}
        style={
          {
            "--dice-ms": `${volley ? volley.diceMs + READ_MS : 0}ms`,
          } as CSSProperties
        }
      >
        <RoundStamp round={view.round} kind={view.kind} />
        <BattleFleet
          side={attacker}
          views={attackerViews}
          align="left"
          name={a.name}
          colorAlias={a.colorAlias}
          maxHp={attackerMax}
          isWinner={view.winner === attacker.faction}
          skipEntry={skipEntry}
          retreat={retreatOf(attacker.faction)}
          assigning={
            view.step === "ASSIGN" && view.assigning === attacker.faction
          }
          marks={view.assigning === attacker.faction ? marks : {}}
          assignable={(ship) => allowedIds.has(ship.id)}
          onToggle={toggle}
          entryKey={`${view.position}|${view.kind}|${view.planet ?? ""}|${attacker.faction}`}
          pick={pickFor(attacker)}
          kind={view.kind === "ground" ? "ground" : "space"}
        />
        <BattleCenter
          view={view}
          nameOf={nameOf}
          colorOf={(key) => players(key).colorAlias}
          busy={busy}
          rolling={rolling}
          onHold={onHold}
          absorbed={covered}
          ready={ready}
          cancels={cancels}
          pickNotes={pickNotes}
          onAfb={() => void run(battleAfb)}
          onAfbExtra={(side, picks) => {
            const playerId = [view.attacker, view.defender].find((s) => s?.faction === side)?.playerId;
            if (playerId) void run(() => battleAfbExtraDice(playerId, picks));
          }}
          afbEditable={(side) => {
            const playerId = [view.attacker, view.defender].find((s) => s?.faction === side)?.playerId;
            return !!playerId && canAct(playerId);
          }}
          onRoll={(side) => void run(() => battleRoll(side))}
          rollEditable={(side) => {
            const playerId = [view.attacker, view.defender].find((s) => s?.faction === side)?.playerId;
            return !!playerId && canAct(playerId);
          }}
          onAuto={() => setMarks(autoMarks(allowedShips, required, cancels))}
          targetNote={targetNote}
          onClearMarks={() => setMarks({})}
          onConfirmAssign={() => {
            if (!view.assigning) return;
            const ids = (...kinds: Mark[]) =>
              new Set(
                Object.entries(marks)
                  .filter(([, m]) => kinds.includes(m))
                  .map(([id]) => id),
              );
            intents.current[view.assigning] = {
              destroy: ids("destroy", "both"),
              sustain: ids("sustain", "both"),
              prefer: new Set(),
              at: Date.now(),
            };
            void run(() =>
              battleAssign(
                view.assigning!,
                planFromMarks(assigningShips, marks),
              ),
            );
          }}
          onClose={() => void run(battleClose)}
          decisionsPending={offersPending}
          reactionLabel={reactionLabel}
          systemLabel={systemLabel}
          onAnnounce={(announce) =>
            view.announcing &&
            void run(() => battleAnnounceRetreat(view.announcing!, announce))
          }
          onRetreat={(destination, ionStormToken) =>
            view.retreating[0] &&
            void run(() => battleRetreat(view.retreating[0], destination, ionStormToken))
          }
        />
        <BattleFleet
          side={defender}
          views={defenderViews}
          align="right"
          name={d.name}
          colorAlias={d.colorAlias}
          maxHp={defenderMax}
          isWinner={view.winner === defender.faction}
          skipEntry={skipEntry}
          retreat={retreatOf(defender.faction)}
          assigning={
            view.step === "ASSIGN" && view.assigning === defender.faction
          }
          marks={view.assigning === defender.faction ? marks : {}}
          assignable={(ship) => allowedIds.has(ship.id)}
          onToggle={toggle}
          entryKey={`${view.position}|${view.kind}|${view.planet ?? ""}|${defender.faction}`}
          pick={pickFor(defender)}
          kind={view.kind === "ground" ? "ground" : "space"}
        />
        {volleys.map((v) => (
          <VolleyLayer
            key={v.id}
            volley={v}
            fieldRef={fieldRef}
            ground={view.kind === "ground"}
          />
        ))}
        <AssaultCannonLayer
          effects={view.effects ?? []}
          fieldRef={fieldRef}
          attacker={attacker.faction}
          nameOf={nameOf}
          unitName={(faction, baseType) => {
            const player = gameData?.playerData?.find((p) => p.faction === faction);
            return lookupUnit(asyncOfBase(baseType), faction, player)?.name ?? baseType;
          }}
        />
        {showPool && <DicePool left={pool.left} right={pool.right} />}
        {volleys
          .filter((v) => v.diceMs > 0)
          .map((v) => (
            <DiceTray
              key={v.id}
              volley={v}
              fromPool={fromPoolOf(v)}
              pool={{ left: pool.left, right: pool.right }}
            />
          ))}
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
/** Jak długo trzymać stan sprzed rzutu: kości na stole + salwa strzałów obu stron. */
function battleHoldMs(view: BattleView): number {
  const entry = view.log[view.log.length - 1];
  if (!entry || entry.phase === "RETREAT" || !view.attacker || !view.defender)
    return 0;
  // Strona, która rzuciła wcześniej osobno, ma już odegraną salwę - czekamy tylko na drugą.
  const early = new Set(entry.early ?? []);
  const left = early.has(view.attacker.faction)
    ? 0
    : countDice(entry.rolls[view.attacker.faction] ?? []);
  const right = early.has(view.defender.faction)
    ? 0
    : countDice(entry.rolls[view.defender.faction] ?? []);
  if (left + right === 0) return 0;
  return volleyStartMs(left, right) + HOLD_TAIL_MS;
}

/**
 * Widok z jednostkami i wynikiem sprzed rzutu; dziennik zostaje żywy (rusza animacja kości).
 * Do końca animacji nie zdradzamy też, KTO trafił: bez panelu przypisania strat (ile trafień
 * pokryć) i bez akcji kolejnego kroku — panel pokazuje „salwa w toku" (``resolving``).
 */
function freezeBattleSides(live: BattleView, before: BattleView): BattleView {
  return {
    ...live,
    attacker: before.attacker,
    defender: before.defender,
    winner: before.winner,
    outcome: before.outcome,
    assigning: null,
    required: {},
    pendingHits: {},
    resolving: true,
  };
}

export function BattleOverlay() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const hidden = useAppStore((s) => s.battleHidden);
  const setHidden = useAppStore((s) => s.setBattleHidden);
  const inCombat = gameState?.activeCombat != null;
  const { data: live } = useBattle(inCombat);
  // Straty z rzutu (np. auto-przypisane neutralnym albo AFB) pokazujemy dopiero po kościach i strzałach.
  const { view, holding } = useDiceHold(live, battleHoldMs, freezeBattleSides);
  // Po walce kolejna bitwa (także w tym samym systemie) znów ma wlot floty.
  const over = !inCombat && !holding;
  // Chwilowy brak walki w odczycie stanu (np. przejście kroku) nie może kasować pamięci wlotu —
  // inaczej flota wlatywała drugi raz. Kasujemy dopiero, gdy walki nie ma przez dłuższą chwilę.
  useEffect(() => {
    if (!over) return;
    const t = window.setTimeout(resetFleetEntries, 4000);
    return () => window.clearTimeout(t);
  }, [over]);
  const offersPending = (gameState?.pendingOffers ?? []).length > 0;

  if (
    (!inCombat && !holding) ||
    !view?.active ||
    !view.attacker ||
    !view.defender
  )
    return null;

  if (hidden) {
    return createPortal(
      <button
        type="button"
        className={styles.returnPill}
        onClick={() => setHidden(false)}
      >
        <IconSwords size={16} aria-hidden="true" />
        Battle in progress — return
      </button>,
      document.body,
    );
  }
  return createPortal(
    <Battlefield
      view={view}
      offersPending={offersPending}
      reactionLabel={gameState?.reactionPause?.label ?? null}
    />,
    document.body,
  );
}

export default BattleOverlay;

/**
 * Plansza nowej rundy: „ROUND 2" przecina pole bitwy na ~2 s, gdy silnik przechodzi do
 * kolejnej rundy (RULES.md 39 — walka toczy się rundami do wyniku). Runda 1 nie ma planszy:
 * jej wstępem jest wejście flot. Czysta prezentacja, bez wpływu na klik (pointer-events: none).
 */
function RoundStamp({ round, kind }: { round: number; kind: string | null | undefined }) {
  const first = useRef(round);
  if (round <= 1 || round === first.current) return null;
  return (
    <div key={round} className={styles.roundStamp} aria-hidden="true">
      <small>{kind === "ground" ? "Ground combat" : "Space combat"}</small>
      <b>Round {round}</b>
    </div>
  );
}

