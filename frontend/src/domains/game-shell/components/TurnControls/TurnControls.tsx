import { useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import {
  IconBolt,
  IconHandStop,
  IconPlayerPlayFilled,
  IconPlayerTrackNextFilled,
  IconChevronsRight,
} from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import {
  useBoardEditor,
  useStrategyCards,
  type StrategyCardState,
} from "@/api/useBoardEditor";
import {
  getStrategyCardById,
  getStrategyCardByInitiative,
} from "@/entities/lookup/strategyCards";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { DetailsCard, type DetailsCardColor } from "@/shared/ui/DetailsCard";
import { Stack } from "@/ds";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { useDeskPlayer } from "./useDeskPlayer";
import styles from "./TurnControls.module.css";

/* Initiative → wariant koloru DetailsCard (tooltip treści) — jak w StrategyCardTable. */
const SC_DETAILS_COLOR: Record<number, DetailsCardColor> = {
  1: "red",
  2: "orange",
  3: "yellow",
  4: "green",
  5: "teal",
  6: "cyan",
  7: "blue",
  8: "violet",
};

/* Initiative → barwa karty (fallback glow, gdy brak colourHexCode w danych). */
const SC_HUE: Record<number, string> = {
  1: "#ec1c24",
  2: "#f69421",
  3: "#fff200",
  4: "#39b54a",
  5: "#00a99d",
  6: "#008ed4",
  7: "#15489f",
  8: "#752b90",
};

/**
 * Sterowanie turą aktywnego gracza — PRZYPIĘTE na mapie, ODDZIELNE od ręki kart.
 *
 * Dwie osobne strefy „jak rzeczy przed graczem":
 *  - .cardZone (lewy dół): karta strategii jako DUŻY obrazek PNG, lekko przechylona
 *    (leży na stole), prostuje się i unosi na hover; zagranie = nakładka „Play"
 *    pojawiająca się na hover (NIE osobny przycisk);
 *  - .actionZone (prawy dół): elegancki panel akcji tury (faza + gracz w nagłówku,
 *    duże przyciski z ikonami i poświatą) — Pass / End turn / Next phase.
 *
 * Render tylko w fazie akcji/strategii i gdy jest aktywny gracz (inaczej null).
 */
export function TurnControls() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: cards } = useStrategyCards();
  const {
    playStrategyCard,
    passTurn,
    endTurn,
    nextPlayer,
    phaseStep,
    nextPhase,
    nextRound,
  } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  // Pulpit widoczny CAŁY CZAS — pokazuje „gracza pulpitu" (aktywny → mówca →
  // pierwszy). Zwraca null tylko, gdy nie ma żadnego posadzonego gracza.
  const active = useDeskPlayer();
  if (!active) return null;

  const phase = gameState?.phase ?? "unknown";
  const isStrategy = phase === "strategy";
  // Pass / End turn mają sens tylko w fazie akcji i dla GRACZA, który faktycznie
  // jest teraz aktywny (nie dla mówcy-fallbacku między turami).
  const isAction = phase === "action" && active.active === true;
  // Dopóki trwa OTWARTE OKNO czasowe (np. secondary karty strategii), aktywny gracz
  // NIE może zakończyć tury — wszyscy inni muszą najpierw zdecydować (RULES.md 31.6).
  // Blokada w UI (czytelna) + twarda walidacja w backendzie (end_turn → 422).
  const windowOpen = gameState?.pendingWindow != null;
  // Status: „Next player" kończy krok gracza (/turn/phase-step). Agenda: „Pass"
  // kończy część gracza (/turn/phase-step), „Next player" tylko przewija (/turn/
  // next-player). „Next phase" u mówcy pojawia się wg ``canAdvancePhase``.
  const isStatus = phase.startsWith("status");
  const isAgenda = phase.startsWith("agenda");
  const isSpeaker =
    gameState?.speaker != null && active.color === gameState.speaker;
  // „Next phase" widzi ZAWSZE mówca (w każdej głównej fazie). Gdy przejście nie jest
  // jeszcze dozwolone (np. nie wszyscy wybrali/spasowali), klik zwróci 422 i panel
  // pokaże komunikat — zgodnie z decyzją „komunikat przy niedozwolonej akcji"
  // (2026-11, uwaga użytkownika). Brak twardego ukrywania przycisku.
  const showNextPhase = isAgenda || isSpeaker;
  // Czytelna etykieta fazy w nagłówku pulpitu.
  const phaseLabel = phase.startsWith("agenda")
    ? "Agenda phase"
    : phase.startsWith("status")
      ? "Status phase"
      : phase === "action"
        ? "Action phase"
        : phase === "strategy"
          ? "Strategy phase"
          : "Turn";
  const myCards = (cards ?? []).filter((c) => c.picked_by === active.discordId);
  const hasCard = myCards.length > 0;
  const played = myCards.some((c) => c.exhausted);
  const canPass = !hasCard || played;
  const activeName = getPlayerFactionDisplayName(active);

  const run = (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    void fn().finally(() => setBusy(false));
  };

  return (
    <>
      {/* STREFA KARTY — karta w SLOCIE (wyznaczone miejsce przy stole). Slot ma
          stały kształt karty i jest widoczny także, gdy karty nie ma (pusty zarys). */}
      <div className={styles.cardZone} aria-label="Your Strategy Card">
        <div className={styles.cards}>
          {hasCard ? (
            myCards.map((card, i) => (
              <div key={card.initiative} className={styles.slot} data-filled>
                <StrategyCardImage
                  card={card}
                  index={i}
                  canPlay={isAction && !card.exhausted}
                  busy={busy}
                  onPlay={() =>
                    run(() => playStrategyCard(active.discordId, card.initiative))
                  }
                />
              </div>
            ))
          ) : (
            <div className={styles.slot}>
              <div className={styles.slotEmpty}>
                <IconBolt size={18} aria-hidden="true" />
                <span>
                  {isStrategy ? "Pick a Strategy Card" : "Strategy Card"}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* STREFA PRZYCISKÓW (prawy dół) — elegancki panel akcji tury. */}
      <div className={styles.actionZone} aria-label="Turn actions">
        <header className={styles.actionHead}>
          {active.faction && (
            <CircularFactionIcon faction={active.faction} size={22} />
          )}
          <span className={styles.actionHeadText}>
            <small className={styles.actionPhase}>{phaseLabel}</small>
            <b className={styles.actionWho}>{activeName}</b>
          </span>
        </header>

        <div className={styles.actionBtns}>
          {/* Faza AKCJI: Pass (po akcji strategicznej) + End turn. */}
          {isAction && (
            <>
              <button
                type="button"
                className={styles.pass}
                style={{ "--d": "0ms" } as CSSProperties}
                disabled={busy}
                onClick={() => run(() => passTurn())}
                title={
                  canPass
                    ? "Pass, then End turn to hand over"
                    : "Play your Strategy Card before passing."
                }
              >
                <IconHandStop size={16} aria-hidden="true" />
                <span>Pass</span>
              </button>
              <button
                type="button"
                className={styles.endTurn}
                style={{ "--d": "60ms" } as CSSProperties}
                disabled={busy || windowOpen}
                onClick={() => run(() => endTurn())}
                title={
                  windowOpen
                    ? "Wait — every player must decide on the secondary first"
                    : "End your turn (also after passing)"
                }
              >
                <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
                <span>End turn</span>
              </button>
            </>
          )}

          {/* Faza STATUS: „Next player" KOŃCZY krok gracza (passed=True) i przesuwa
              dalej — po komplecie kroków mówca dostaje „Next phase". Wołamy BEZ
              player_id: backend adresuje swojego ``active_player_id`` (unikamy
              rozjazdu „gracza pulpitu" useDeskPlayer z realnym aktywnym — BUG 1). */}
          {isStatus && (
            <button
              type="button"
              className={styles.endTurn}
              style={{ "--d": "0ms" } as CSSProperties}
              disabled={busy}
              onClick={() => run(() => phaseStep())}
              title="Finish your Status step and pass to the next player"
            >
              <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
              <span>Next player</span>
            </button>
          )}

          {/* Faza AGENDA: „Pass" KOŃCZY część gracza (reakcja/głos), „Next player"
              tylko przewija wskaźnik bez kończenia kogokolwiek. Oba BEZ player_id —
              backend adresuje swojego aktywnego gracza. */}
          {isAgenda && (
            <>
              <button
                type="button"
                className={styles.pass}
                style={{ "--d": "0ms" } as CSSProperties}
                disabled={busy}
                onClick={() => run(() => phaseStep())}
                title="Pass — decline your reaction/vote this agenda"
              >
                <IconHandStop size={16} aria-hidden="true" />
                <span>Pass</span>
              </button>
              <button
                type="button"
                className={styles.endTurn}
                style={{ "--d": "60ms" } as CSSProperties}
                disabled={busy}
                onClick={() => run(() => nextPlayer())}
                title="Pass the floor to the next player (no pass recorded)"
              >
                <IconPlayerTrackNextFilled size={16} aria-hidden="true" />
                <span>Next player</span>
              </button>
            </>
          )}

          {/* Przejście fazy OGŁASZA MÓWCA, i to tylko gdy wolno (``showNextPhase``):
              akcja/status po komplecie pasów/kroków; strategia po pełnym wyborze.
              PO AGENDZIE = nowa runda (runda +1, reset pasów, TG na niewybranych
              kartach) — wołamy /round/next zamiast /phase/next. */}
          {showNextPhase && (
            <button
              type="button"
              className={styles.nextPhase}
              style={{ "--d": isAction ? "120ms" : "60ms" } as CSSProperties}
              disabled={busy}
              onClick={() => run(isAgenda ? nextRound : nextPhase)}
              title={
                isAgenda
                  ? "End the agenda phase and start the next round"
                  : "Advance to the next phase"
              }
            >
              <IconChevronsRight size={16} aria-hidden="true" />
              <span>{isAgenda ? "Next round" : "Next phase"}</span>
            </button>
          )}
        </div>

        {/* Podpowiedź, gdy Pass zablokowany (zanim zagrasz kartę). */}
        {isAction && !canPass && (
          <p className={styles.hint}>Play your Strategy Card first to pass.</p>
        )}
        {/* Podpowiedź, gdy End turn zablokowany przez otwarte okno secondary. */}
        {isAction && windowOpen && (
          <p className={styles.hint}>
            Waiting for every player to follow or decline the secondary.
          </p>
        )}
      </div>
    </>
  );
}

/**
 * Jedna karta strategii w slocie: obrazek PNG + nakładka „Play"/„Played" na hover
 * ORAZ tooltip z treścią karty (Primary/Secondary) — ten sam wzorzec, co w fazie
 * strategii (``SmoothPopover`` + ``DetailsCard``). Hover otwiera tooltip i pokazuje
 * akcję „Play"; karta jednocześnie prostuje się i unosi ze slotu (CSS).
 */
function StrategyCardImage({
  card,
  index,
  canPlay,
  busy,
  onPlay,
}: {
  card: StrategyCardState;
  index: number;
  canPlay: boolean;
  busy: boolean;
  onPlay: () => void;
}) {
  const [failed, setFailed] = useState(false);
  const [hovered, setHovered] = useState(false);
  const def =
    getStrategyCardById(card.id) ?? getStrategyCardByInitiative(card.initiative);
  const imageURL = def?.imageURL;
  const showImage = !!imageURL && !failed;
  const name = card.name || SC_NAMES[card.initiative] || "—";
  const hue = def?.colourHexCode || SC_HUE[card.initiative] || "#888";
  const detailsColor =
    SC_DETAILS_COLOR[card.initiative] ?? ("none" as DetailsCardColor);
  const primaryText = (def?.primaryTexts ?? []).join("\n\n");
  const secondaryText = (def?.secondaryTexts ?? []).join("\n\n");

  return (
    <SmoothPopover opened={hovered} position="top" onChange={setHovered}>
      <SmoothPopover.Target>
        <div
          className={styles.card}
          data-played={card.exhausted || undefined}
          style={
            {
              "--sc-hue": hue,
              "--i": index,
            } as CSSProperties
          }
          title={name}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onFocus={() => setHovered(true)}
          onBlur={() => setHovered(false)}
        >
          <div className={styles.cardInner}>
            {showImage ? (
              <img
                className={styles.cardImage}
                src={imageURL}
                alt={name}
                loading="lazy"
                onError={() => setFailed(true)}
              />
            ) : (
              <div className={styles.cardFallback}>
                <span className={styles.disc}>{card.initiative}</span>
                <span className={styles.name}>{name}</span>
              </div>
            )}

            {/* Nakładka na hover: Play (niezagrana) albo znacznik Played. */}
            {canPlay ? (
              <button
                type="button"
                className={styles.playOverlay}
                disabled={busy}
                onClick={onPlay}
                title={`Play ${name} (primary + secondary window)`}
              >
                <IconPlayerPlayFilled size={22} aria-hidden="true" />
                <span>Play</span>
              </button>
            ) : card.exhausted ? (
              <span className={styles.playedBadge}>Played</span>
            ) : null}
          </div>
        </div>
      </SmoothPopover.Target>

      {/* Tooltip treści karty — jak w StrategyCardTable (Primary/Secondary). */}
      <SmoothPopover.Dropdown p={0}>
        <DetailsCard width={340} color={detailsColor}>
          <Stack gap="md">
            <DetailsCard.Title
              title={`${def?.initiative ?? card.initiative} ${def?.name ?? name}`}
              subtitle={`Strategy card · Initiative ${def?.initiative ?? card.initiative}`}
            />
            {primaryText && (
              <DetailsCard.Section title="Primary" content={primaryText} />
            )}
            {secondaryText && (
              <DetailsCard.Section title="Secondary" content={secondaryText} />
            )}
          </Stack>
        </DetailsCard>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

export default TurnControls;
