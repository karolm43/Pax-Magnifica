// Okno setupu startowego gry (RULES.md 45): pojawia się po „Start gry" / odświeżeniu strony,
// dopóki backend trzyma `gameState.setup`. Trzy etapy:
//
//  1. SECRETS    — każdy gracz po kolei dobiera 2 tajne cele i zatrzymuje 1 (drugi wraca do
//                  talii). Karty widzi TYLKO wybierający (bramka „przekaż ekran" dla hot-seat;
//                  docelowo w grze sieciowej backend wyśle kandydatów tylko właścicielowi);
//  2. CUSTODIANS — mówca kładzie żeton Custodians na Mecatol Rex;
//  3. OBJECTIVES — 5+5 zakrytych celów publicznych; mówca klika i odsłania dwa cele I etapu.
//
// Okno jest NIEODRZUCALNE (setup trzeba domknąć, zanim ruszy faza strategii). Po odkryciu
// celów zostaje jeszcze na chwilę, by pokazać odwrócone karty, i zamyka się przyciskiem.

import { useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getPublicObjective } from "@/entities/lookup/publicObjectives";
import { SecretObjectiveCard } from "@/domains/cards/components/SecretObjectiveCard";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import type { GameSetup, GameSetupPlayer } from "@/entities/data/types";
import styles from "./GameSetupOverlay.module.css";

/** Ile celów I etapu odkrywa mówca (zgodne z backendem: `REVEALED_AT_SETUP`). */
const REVEAL_COUNT = 2;
const STAGE_SLOTS = 5;

const COLOR_SWATCH: Record<string, string> = {
  red: "#d94a4a",
  green: "#49a14a",
  white: "#e8e8e8",
  blue: "#4a7fd9",
  purple: "#9a4ad9",
  yellow: "#e0c23a",
};

const STAGE_TITLES: Record<GameSetup["stage"], string> = {
  SECRETS: "Secret objectives",
  CUSTODIANS: "Custodians token",
  OBJECTIVES: "Public objectives",
};

function playerSwatch(player?: GameSetupPlayer): CSSProperties {
  const color = player?.color ? COLOR_SWATCH[player.color] : undefined;
  return color ? ({ "--player": color } as CSSProperties) : {};
}

export function GameSetupOverlay() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { setupSecret, setupCustodians, setupRevealObjectives, setupSkip } = useBoardEditor();

  const setup = gameState?.setup ?? null;
  const [busy, setBusy] = useState(false);
  // Gracz, któremu przekazano ekran (bramka przed pokazaniem jego tajnych celów).
  const [readyFor, setReadyFor] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  // Po kliknięciu „odkryj" setup znika z backendu, a okno zostaje na pokaz odwróconych kart.
  const [revealedByUs, setRevealedByUs] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // Po zako?czeniu setupu okno ?yje jeszcze tylko jako pokaz odkrytych cel?w (`finished`).
  const finished = !setup && revealedByUs;
  if (!setup && (dismissed || !revealedByUs)) return null;

  const run = (action: () => Promise<void>, after?: () => void) => {
    if (busy) return;
    setBusy(true);
    void action()
      .then(after)
      .catch(() => undefined) // powód błędu pokazuje już `notice` z hooka
      .finally(() => setBusy(false));
  };

  const players = setup?.players ?? [];
  const speaker = players.find((p) => p.id === setup?.speakerId);

  // Odkryte cele I etapu (po kliknięciu mówcy) — z dokumentu web-data.
  const revealedKeys = (gameData?.objectives?.stage1Objectives ?? [])
    .filter((o) => o.revealed)
    .map((o) => o.key);

  const stage = setup?.stage ?? "OBJECTIVES";
  const content = (() => {
    if (!setup) {
      return (
        <ObjectivesStage
          stage1Hidden={Math.max(STAGE_SLOTS - REVEAL_COUNT, 0)}
          stage2Hidden={STAGE_SLOTS}
          revealedKeys={revealedKeys}
          speakerName={speaker?.name ?? ""}
          done
          busy={busy}
          onReveal={() => undefined}
        />
      );
    }
    if (setup.stage === "SECRETS") {
      const chooser = players.find((p) => p.id === setup.chooserId);
      return (
        <SecretsStage
          setup={setup}
          chooser={chooser}
          ready={readyFor === setup.chooserId}
          picked={picked}
          busy={busy}
          onReady={() => setReadyFor(setup.chooserId)}
          onPick={setPicked}
          onConfirm={() => {
            if (!chooser || !picked) return;
            run(
              () => setupSecret(chooser.id, picked),
              () => {
                setPicked(null);
                setReadyFor(null);
              },
            );
          }}
        />
      );
    }
    if (setup.stage === "CUSTODIANS") {
      return (
        <CustodiansStage
          speakerName={speaker?.name ?? "The speaker"}
          busy={busy}
          onPlace={() => speaker && run(() => setupCustodians(speaker.id))}
        />
      );
    }
    return (
      <ObjectivesStage
        stage1Hidden={setup.stage1Hidden}
        stage2Hidden={setup.stage2Hidden}
        revealedKeys={[]}
        speakerName={speaker?.name ?? "The speaker"}
        done={false}
        busy={busy}
        onReveal={() =>
          speaker &&
          run(
            () => setupRevealObjectives(speaker.id),
            () => {
              setDismissed(false);
              setRevealedByUs(true);
            },
          )
        }
      />
    );
  })();

  return createPortal(
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-label="Game setup"
    >
      <div className={styles.panel}>
        <header className={styles.header}>
          <p className={styles.kicker}>Game setup</p>
          <h1 className={styles.title}>
            {finished || !setup ? STAGE_TITLES.OBJECTIVES : STAGE_TITLES[stage]}
          </h1>
          <SetupProgress stage={finished || !setup ? "DONE" : stage} />
        </header>

        {setup && setup.stage === "SECRETS" && (
          <ul className={styles.roster} aria-label="Players">
            {players.map((p) => (
              <li
                key={p.id}
                className={`${styles.rosterItem} ${
                  p.id === setup.chooserId ? styles.rosterActive : ""
                }`}
                style={playerSwatch(p)}
              >
                {p.faction ? <CircularFactionIcon faction={p.faction} size={26} /> : null}
                <span>{p.name}</span>
                <span className={styles.rosterState}>
                  {p.chosen ? "✓ chosen" : p.id === setup.chooserId ? "choosing…" : "waiting"}
                </span>
              </li>
            ))}
          </ul>
        )}

        <div className={styles.body}>{content}</div>

        {setup && (
          <footer className={styles.footer}>
            <button
              type="button"
              className={styles.primary}
              disabled={busy}
              title="Random secret objectives, Custodians token placed, two Stage I objectives revealed"
              onClick={() =>
                run(
                  () => setupSkip(),
                  () => {
                    setPicked(null);
                    setReadyFor(null);
                    setDismissed(true);
                  },
                )
              }
            >
              Skip setup (random)
            </button>
          </footer>
        )}

        {finished && (
          <footer className={styles.footer}>
            <button
              type="button"
              className={styles.primary}
              onClick={() => setDismissed(true)}
              autoFocus
            >
              Begin the Strategy Phase
            </button>
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}

const PROGRESS_STEPS: { id: GameSetup["stage"]; label: string }[] = [
  { id: "SECRETS", label: "Secrets" },
  { id: "CUSTODIANS", label: "Custodians" },
  { id: "OBJECTIVES", label: "Objectives" },
];

function SetupProgress({ stage }: { stage: GameSetup["stage"] | "DONE" }) {
  const current = stage === "DONE" ? PROGRESS_STEPS.length : PROGRESS_STEPS.findIndex((s) => s.id === stage);
  return (
    <ol className={styles.progress} aria-label="Setup progress">
      {PROGRESS_STEPS.map((step, index) => (
        <li
          key={step.id}
          className={`${styles.progressItem} ${
            index < current ? styles.progressDone : index === current ? styles.progressNow : ""
          }`}
          aria-current={index === current ? "step" : undefined}
        >
          {step.label}
        </li>
      ))}
    </ol>
  );
}

/* ── Etap 1: tajne cele ──────────────────────────────────────────────────── */

type SecretsStageProps = {
  setup: GameSetup;
  chooser?: GameSetupPlayer;
  ready: boolean;
  picked: string | null;
  busy: boolean;
  onReady: () => void;
  onPick: (id: string) => void;
  onConfirm: () => void;
};

function SecretsStage({
  setup,
  chooser,
  ready,
  picked,
  busy,
  onReady,
  onPick,
  onConfirm,
}: SecretsStageProps) {
  const name = chooser?.name ?? "Player";
  if (!chooser) {
    return <p className={styles.lead}>Waiting for the next player…</p>;
  }
  // Bramka hot-seat: dopóki wybierający nie potwierdzi, że to on patrzy, karty są zakryte.
  if (!ready) {
    return (
      <div className={styles.gate} style={playerSwatch(chooser)}>
        {chooser.faction ? <CircularFactionIcon faction={chooser.faction} size={72} /> : null}
        <p className={styles.lead}>
          <b>{name}</b>, you draw two secret objectives and keep one.
        </p>
        <p className={styles.hint}>Make sure only you can see the screen.</p>
        <button type="button" className={styles.primary} onClick={onReady} autoFocus>
          I'm {name} — show my objectives
        </button>
      </div>
    );
  }
  return (
    <div className={styles.secrets} style={playerSwatch(chooser)}>
      <p className={styles.lead}>
        <b>{name}</b>, choose the objective you keep. The other one is shuffled back into the
        secret objective deck.
      </p>
      <div className={styles.choices}>
        {setup.candidates.map((id) => (
          <button
            key={id}
            type="button"
            className={`${styles.choice} ${picked === id ? styles.choicePicked : ""}`}
            aria-pressed={picked === id}
            onClick={() => onPick(id)}
          >
            <SecretObjectiveCard secretId={id} />
          </button>
        ))}
      </div>
      <button
        type="button"
        className={styles.primary}
        disabled={!picked || busy}
        onClick={onConfirm}
      >
        Keep this objective
      </button>
    </div>
  );
}

/* ── Etap 2: żeton Custodians ───────────────────────────────────────────── */

function CustodiansStage({
  speakerName,
  busy,
  onPlace,
}: {
  speakerName: string;
  busy: boolean;
  onPlace: () => void;
}) {
  return (
    <div className={styles.custodians}>
      <img
        className={styles.custodianToken}
        src={assetUrl("/tokens/token_custodian.png")}
        alt="Custodians token"
      />
      <p className={styles.lead}>
        <b>{speakerName}</b> (speaker) places the Custodians token on Mecatol Rex.
      </p>
      <p className={styles.hint}>
        Landing ground forces on Mecatol Rex requires spending 6 influence and removes the token.
      </p>
      <button type="button" className={styles.primary} disabled={busy} onClick={onPlace}>
        Place on Mecatol Rex
      </button>
    </div>
  );
}

/* ── Etap 3: cele publiczne ─────────────────────────────────────────────── */

type ObjectivesStageProps = {
  stage1Hidden: number;
  stage2Hidden: number;
  /** Klucze odkrytych celów I etapu (po odkryciu — odwracają pierwsze karty). */
  revealedKeys: string[];
  speakerName: string;
  done: boolean;
  busy: boolean;
  onReveal: () => void;
};

function ObjectivesStage({
  stage1Hidden,
  stage2Hidden,
  revealedKeys,
  speakerName,
  done,
  busy,
  onReveal,
}: ObjectivesStageProps) {
  const revealed = revealedKeys.slice(0, REVEAL_COUNT);
  return (
    <div className={styles.objectives}>
      <ObjectiveRow
        label="Stage I"
        back="/player_area/cardback_public1.png"
        revealed={revealed}
        hidden={stage1Hidden}
        openSlots={done ? REVEAL_COUNT : 0}
        flip={done}
      />
      <ObjectiveRow
        label="Stage II"
        back="/player_area/cardback_public2.png"
        revealed={[]}
        hidden={stage2Hidden}
        openSlots={0}
        flip={false}
      />
      {done ? (
        <p className={styles.lead}>
          The first two Stage I objectives are open. The remaining eight stay hidden until the
          Status Phase.
        </p>
      ) : (
        <button
          type="button"
          className={styles.revealBox}
          disabled={busy}
          onClick={onReveal}
        >
          <span className={styles.revealTitle}>Reveal two Stage I objectives</span>
          <span className={styles.revealHint}>
            <b>{speakerName}</b> (speaker) clicks to turn the first two cards face up
          </span>
        </button>
      )}
    </div>
  );
}

function ObjectiveRow({
  label,
  back,
  revealed,
  hidden,
  openSlots,
  flip,
}: {
  label: string;
  back: string;
  /** Klucze kart, które będą odwrócone (zajmują pierwsze miejsca w rzędzie). */
  revealed: string[];
  /** Karty nadal zakryte po odkryciu. */
  hidden: number;
  /** Miejsca na odkryte karty (0 przed odkryciem — wtedy `hidden` obejmuje wszystkie). */
  openSlots: number;
  flip: boolean;
}) {
  // `flip` = setup domknięty; odwracamy karty odkryte (jeśli dane jeszcze nie dotarły,
  // karta zostaje rewersem do czasu odświeżenia web-data).
  const total = hidden + openSlots;
  const slots = Array.from({ length: Math.max(total, 0) }, (_, i) => i);
  return (
    <section className={styles.row} aria-label={`${label} objectives`}>
      <h2 className={styles.rowLabel}>{label}</h2>
      <div className={styles.cards}>
        {slots.map((i) => {
          const key = flip ? revealed[i] : undefined;
          const data = key ? getPublicObjective(key) : undefined;
          return (
            <div
              key={i}
              className={`${styles.card} ${data ? styles.cardFlipped : ""}`}
              style={{ "--i": i } as CSSProperties}
            >
              <img className={styles.cardBack} src={assetUrl(back)} alt="Hidden objective" />
              {data && (
                <div className={styles.cardFront}>
                  <b className={styles.cardName}>{data.name}</b>
                  <span className={styles.cardText}>{data.text}</span>
                  <span className={styles.cardPoints}>{data.points} VP</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default GameSetupOverlay;
