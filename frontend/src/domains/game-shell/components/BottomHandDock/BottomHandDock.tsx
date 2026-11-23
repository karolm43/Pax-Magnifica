import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import cx from "clsx";
import {
  IconChevronDown,
  IconLayoutGrid,
  IconPlayerPlayFilled,
  IconTrash,
} from "@tabler/icons-react";
import { UnstyledButton } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { useFactionColors } from "@/hooks/useFactionColors";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { getRelicData } from "@/entities/lookup/relics";
import { getExploration } from "@/entities/lookup/explorations";
import { Tech } from "@/domains/player/components/Tech";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { usePlayerData } from "@/api/usePlayerData";
import {
  loadStoredChoice,
  saveStoredChoice,
} from "@/utils/localStorageSettings";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import type { PlayerData } from "@/entities/data/types";
import { HoldControls } from "./HoldControls";
import { KnownCards } from "./KnownCards";
import {
  DRAG_TYPE,
  FRONTIER_DRAG_TYPE,
  HandCard,
  TABS,
  type CardTab,
  type HandTab,
} from "./HandCard";
import { UndoControls } from "./UndoControls";
import { ReactionPauseBanner } from "./ReactionPauseBanner";
import { HeldPlayBanner } from "./HeldPlayBanner";
import { useDockCovered } from "./useDockCovered";
import { ActionCardPlayModal } from "@/domains/game-shell/components/TurnControls/ActionCardPlayModal";
import {
  postDiscardExcess,
  useActionCardPlayability,
  useHandLimit,
} from "@/api/useActionCard";
import { useQueryClient } from "@tanstack/react-query";
import { useRelicPlayability } from "@/api/useRelics";
import { usePromissoryPlayability } from "@/api/useFactionComponents";
import { RelicForgePanel } from "@/domains/relics/RelicForgePanel";
import { readyReactions } from "./reactionReady";
import { playUi } from "@/shared/audio/uiSounds";
import styles from "./BottomHandDock.module.css";

/**
 * „Pasek ręki" aktywnego gracza u dołu mapy — styl stołu (TTS): karty leżą
 * wachlarzem jako kafelki z rewersem i nazwą, kliknięcie odsłania pełną kartę
 * (treść + grafika rewersu). Trzy kategorie jako segmenty z licznikami: karty
 * akcji, tajne cele i promissory notes (weksle). Rękę bierze z endpointu
 * ``/game/{id}/hand`` (usePlayerHand z pominięciem bramki — tryb lokalny,
 * operator widzi wszystko), który zwraca rękę AKTYWNEGO gracza.
 *
 * Podgląd jak przy fizycznym stole + ZAGRYWANIE: kartę akcji można przeciągnąć z ręki na strefę
 * „Drop to play" (otwiera formularz zagrania). Podnieść można tylko kartę, którą silnik pozwala
 * zagrać teraz (`/action-card/playable`: tura, faza, okno ACTION, legalne cele); pozostałe są
 * przyciemnione, a podpowiedź mówi dlaczego.
 *
 * Zakładka „Relics" pokazuje relikty gracza (leżą przed nim, nie w ręce). Te z „ACTION:" działają
 * jak karty akcji (`/relic/playable`, ta sama strefa zagrania; relikt zostaje po zagraniu),
 * pasywne są tylko do obejrzenia - działają same i są też w panelu gracza.
 *
 * Zakładka „Techs" to technologie gracza (te same kafelki `Tech` co w panelu gracza, klik =
 * pełna karta); najpierw te, które działają w turze (dawny rząd nad kartą strategii).
 */

const EMPTY_COPY: Record<HandTab, string> = {
  actions: "No action cards in hand",
  secrets: "No secret objectives in hand",
  notes: "No promissory notes in hand",
  relics: "No relics in play",
  techs: "No technologies",
};

const DOCK_OPEN_KEY = "ti4_bottom_hand_dock_open";

function useDockOpen(): [boolean, (next: boolean) => void] {
  const [open, setOpen] = useState(() => {
    const stored = loadStoredChoice(DOCK_OPEN_KEY, ["true", "false"]);
    return stored === null ? true : stored === "true";
  });
  const set = (next: boolean) => {
    setOpen(next);
    saveStoredChoice(DOCK_OPEN_KEY, String(next), "bottom hand dock state");
  };
  return [open, set];
}

/**
 * Technologie gracza w doku ręki: najpierw działające w turze (Fleet Logistics, Transit
 * Diodes, Bio-Stims…), potem reszta. Te same kafelki `Tech` co w panelu gracza.
 */
function TechFan({ player }: { player: PlayerData }) {
  const exhausted = new Set(player.exhaustedTechs);
  const turn = new Set(
    (player.techEffects ?? []).filter((t) => t.contexts.includes("turn")).map((t) => t.alias),
  );
  const groups = [
    { label: "This turn", ids: player.techs.filter((id) => turn.has(id)) },
    { label: turn.size ? "Other" : "", ids: player.techs.filter((id) => !turn.has(id)) },
  ].filter((g) => g.ids.length > 0);
  if (groups.length === 0) {
    return (
      <p className={styles.empty}>
        <IconLayoutGrid size={14} aria-hidden="true" />
        {EMPTY_COPY.techs}
      </p>
    );
  }
  return (
    <div className={styles.techFan} role="tabpanel">
      {groups.map((g) => (
        <div key={g.label || "all"} className={styles.techGroup} role="list" aria-label={g.label || "Technologies"}>
          {g.label && <span className={styles.techGroupLabel}>{g.label}</span>}
          {g.ids.map((id) => (
            <div key={id} role="listitem">
              <Tech techId={id} isExhausted={exhausted.has(id)} playerId={player.discordId ?? undefined} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export function BottomHandDock() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  // „Gracz pulpitu" — aktywny → mówca → pierwszy posadzony. Dzięki temu dok ręki
  // jest widoczny CAŁY CZAS (także w status/agenda, gdy brak aktywnego gracza).
  const deskPlayer = useDeskPlayer();
  // Ręka = zawsze gracz pulpitu (bez podglądu cudzych rąk — decyzja użytkownika 2026-11-14).
  const active = deskPlayer;

  const { data: hand } = usePlayerHand(gameId, {
    ignoreAuthGate: true,
    player: active?.discordId ?? null,
  });
  const [storedOpen, setStoredOpen] = useDockOpen();
  // Przy oknie pełnoekranowym albo oknie decyzji, które wchodzi na rękę (U3), dok startuje
  // ZWINIĘTY; rozwinięcie w tym czasie jest chwilowe (`peek`) i nie nadpisuje zapamiętanego
  // wyboru gracza. Dok leży NAD tymi oknami (karty reakcji, RULES.md 53.5), więc rozwinięty
  // zasłaniałby ich dół.
  const [dockNode, setDockNode] = useState<HTMLElement | null>(null);
  const overlayOpen = useDockCovered(dockNode);
  const [peek, setPeek] = useState(false);
  useEffect(() => {
    if (!overlayOpen) setPeek(false);
  }, [overlayOpen]);
  const open = overlayOpen ? peek : storedOpen;
  const setOpen = (next: boolean) => (overlayOpen ? setPeek(next) : setStoredOpen(next));
  const [tab, setTab] = useState<HandTab>("actions");
  // Przeciąganie karty akcji na strefę zagrania; po upuszczeniu otwiera formularz (RULES.md 53).
  const [dragCard, setDragCard] = useState<{
    id: string;
    tab: HandTab;
    frontier?: boolean;
    /** Przeciąganie na stos odrzuconych (ręka ponad limitem), nie zagranie. */
    discard?: boolean;
  } | null>(null);
  const [zoneOver, setZoneOver] = useState(false);
  const [playingCard, setPlayingCard] = useState<{
    id: string;
    tab: HandTab;
    frontier?: boolean;
  } | null>(null);
  // Karty akcji i notki sprawdzamy ZAWSZE (nie tylko przy otwartej zakładce): okno reakcji mija
  // z następnym krokiem gry, więc dok musi je zasygnalizować także zwinięty (RULES.md 54.8).
  const { data: playability } = useActionCardPlayability(
    active?.discordId ?? null,
    (hand?.actionCards.length ?? 0) > 0,
  );
  // Limit ręki (R_action_cards, RULES.md 53.8): nadwyżkę gracz odrzuca SAM, przeciągając karty.
  const { data: handLimit } = useHandLimit(
    active?.discordId ?? null,
    (hand?.actionCards.length ?? 0) > 0,
  );
  const mustDiscard = handLimit?.discard ?? 0;
  const [discardError, setDiscardError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const discardCard = async (cardId: string) => {
    if (!active?.discordId) return;
    const error = await postDiscardExcess(active.discordId, cardId);
    setDiscardError(error);
    for (const key of ["playerHand", "actionCardPlayable"]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  };
  // Nadwyżka sama się pokazuje: dok otwiera się na kartach akcji (komponent wyskakuje sam).
  // Tylko przy POJAWIENIU się nadwyżki (zmiana false → true), więc ref zamiast zależności.
  const overLimit = mustDiscard > 0;
  const surfaced = useRef(false);
  useEffect(() => {
    if (!overLimit) {
      surfaced.current = false;
      return;
    }
    if (surfaced.current) return;
    surfaced.current = true;
    setTab("actions");
    if (overlayOpen) setPeek(true);
    else setStoredOpen(true);
  });
  const { data: relicPlayability } = useRelicPlayability(
    active?.discordId ?? null,
    open && tab === "relics",
  );
  const noteColors = useFactionColors();
  // Promissory notes (RULES.md 61.2): zagrywalne w otwartym oknie, nigdy własne.
  const { data: notePlayability } = usePromissoryPlayability(
    active?.discordId ?? null,
    (hand?.promissoryNotes.length ?? 0) > 0,
  );
  const reactions = useMemo(
    () => readyReactions(playability, notePlayability),
    [playability, notePlayability],
  );
  const reactionTabs = useMemo(
    () => new Set<HandTab>(reactions.map((r) => r.tab)),
    [reactions],
  );
  const reactionIds = useMemo(
    () => new Set(reactions.map((r) => `${r.tab}:${r.id}`)),
    [reactions],
  );
  // Karta, której okno minęło ostatnim krokiem (Public Disgrace): zagranie przez hold-rewind.
  const holdSeq =
    playingCard && playingCard.tab === "actions" && !playingCard.frontier
      ? playability?.[playingCard.id]?.hold_seq
      : undefined;
  // Karty frontier (Enigmatic Device) są jawne i wchodzą do zakładki Action cards.
  const frontierIds = useMemo(() => active?.frontierCards ?? [], [active?.frontierCards]);
  const { data: frontierPlayability } = useRelicPlayability(
    active?.discordId ?? null,
    open && tab === "actions" && frontierIds.length > 0,
    "frontier-card",
  );
  // Relikty są jawne (leżą przed graczem), więc lista idzie z danych gracza, nie z endpointu ręki.
  const relicIds = useMemo(() => active?.relics ?? [], [active?.relics]);
  const exhaustedRelics = useMemo(
    () => new Set(active?.exhaustedRelics ?? []),
    [active?.exhaustedRelics],
  );

  const counts = useMemo(
    () => ({
      actions: (hand?.actionCards.length ?? 0) + frontierIds.length,
      secrets: hand?.secretObjectives.length ?? 0,
      notes: hand?.promissoryNotes.length ?? 0,
      relics: relicIds.length,
      techs: active?.techs.length ?? 0,
    }),
    [hand, relicIds, frontierIds, active?.techs.length],
  );

  const ids = useMemo(() => {
    if (tab === "relics") return relicIds;
    if (tab === "techs") return [] as string[];
    if (!hand) return [] as string[];
    if (tab === "actions") return [...hand.actionCards, ...frontierIds];
    if (tab === "secrets") return hand.secretObjectives;
    return hand.promissoryNotes;
  }, [hand, tab, relicIds, frontierIds]);

  // Wiedza z kart i zdolności „look at…”: talia agend (Insider Information, Politics - trwa, aż
  // talia się zmieni, RULES.md 53.5.a1), tajne cele (Extreme Duress), stały podgląd M'aban.
  const { data: mabanPeek } = usePlayerData(gameId, { select: (d) => d.gameState?.peek ?? null });
  const { data: players } = usePlayerData(gameId, { select: (d) => d.playerData ?? [] });
  const known = (
    <KnownCards
      agendaTop={hand?.agendaPeek ?? []}
      agendaBottom={hand?.agendaPeekBottom ?? []}
      revealedSecrets={hand?.revealedSecrets ?? {}}
      maban={mabanPeek ?? null}
      players={players ?? []}
    />
  );
  const hasKnown =
    (hand?.agendaPeek?.length ?? 0) > 0 ||
    (hand?.agendaPeekBottom?.length ?? 0) > 0 ||
    Object.keys(hand?.revealedSecrets ?? {}).length > 0 ||
    Boolean(mabanPeek);

  // Mierzymy wysokość doku (zwinięty / rozwinięty) i wystawiamy ją jako zmienną CSS
  // ``--hand-dock-clear`` na <html> - pastylki powrotu do okien (produkcja, technologie…)
  // ustawiają się NAD dokiem, także gdy wachlarz kart jest otwarty.
  useEffect(() => {
    const root = document.documentElement;
    if (!dockNode) {
      root.style.removeProperty("--hand-dock-clear");
      return;
    }
    const update = () => {
      const top = dockNode.getBoundingClientRect().top;
      root.style.setProperty(
        "--hand-dock-clear",
        `${Math.max(0, Math.round(window.innerHeight - top))}px`,
      );
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(dockNode);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
      root.style.removeProperty("--hand-dock-clear");
    };
  }, [dockNode]);

  // Dock pojawia się tylko, gdy jest aktywny gracz (jego rękę pokazujemy).
  if (!active) return null;

  return (
    <>
    <section
      ref={setDockNode}
      className={styles.dock}
      data-open={open || undefined}
      aria-label="Your hand"
    >
      <div className={styles.bar}>
        <span className={styles.who}>
          {active.faction && (
            <CircularFactionIcon faction={active.faction} size={20} />
          )}
          <span className={styles.whoName}>
            {active.flexibleDisplayName || active.faction || "Active player"}
          </span>
        </span>

        {/* Segmenty kategorii z licznikami (jak zakładki ręki). */}
        <div className={styles.tabs} role="tablist" aria-label="Hand category">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={tab === t.key}
                className={styles.tab}
                style={{ "--hk": t.tone } as CSSProperties}
                data-active={tab === t.key || undefined}
                data-reaction={reactionTabs.has(t.key) || undefined}
                title={
                  reactionTabs.has(t.key)
                    ? "A reaction card here can be played right now"
                    : undefined
                }
                onClick={() => setTab(t.key)}
              >
                <Icon size={14} aria-hidden="true" />
                <span className={styles.tabLabel}>{t.label}</span>
                <b className={styles.tabCount}>{counts[t.key]}</b>
              </button>
            );
          })}
        </div>

        <div className={styles.tools}>
        {active.discordId && <UndoControls playerId={active.discordId} />}
        {active.discordId && <HoldControls playerId={active.discordId} />}
        <span className={styles.toolsSep} aria-hidden="true" />

        <UnstyledButton
          className={styles.collapse}
          aria-expanded={open}
          aria-label={open ? "Collapse hand" : "Expand hand"}
          title={open ? "Collapse hand" : "Expand hand"}
          onClick={() => setOpen(!open)}
        >
          <IconChevronDown
            size={16}
            className={cx(styles.chevron, open && styles.chevronOpen)}
            aria-hidden="true"
          />
        </UnstyledButton>
        </div>
      </div>

      {/* Rozwinięta część ma STAŁĄ wysokość (CSS ``.body``) - nie skacze zależnie od zakładki
          i liczby kart; nadmiar przewija się w środku. */}
      {open && (
      <div
        className={styles.body}
        // Pusta zakładka (np. brak kart akcji na starcie) nie trzyma 176 px pustej tacy
        // nad planszą - ręka kurczy się do jednej linii komunikatu.
        data-empty={
          (tab !== "techs" && tab !== "relics" && ids.length === 0 && !hasKnown) ||
          undefined
        }
      >
      {hasKnown && known}

      {/* Fragmenty -> relikt (RULES.md 59.7): przycisk „Forge relic" nad reliktami. */}
      {tab === "relics" && active.discordId && (
        <RelicForgePanel playerId={active.discordId} enabled />
      )}


      {tab === "techs" && <TechFan player={active} />}

      {tab !== "techs" && (
        <div className={styles.fan} role="tabpanel">
          {ids.length === 0 ? (
            <p className={styles.empty}>
              <IconLayoutGrid size={14} aria-hidden="true" />
              {EMPTY_COPY[tab]}
            </p>
          ) : (
            ids.map((id, index) => {
              const relic = tab === "relics" ? relicPlayability?.[id] : undefined;
              const passive = relic?.kind === "passive";
              const relicTag =
                tab === "relics"
                  ? [
                      relic ? (passive ? "Passive" : "Action") : undefined,
                      exhaustedRelics.has(id) ? "Exhausted" : undefined,
                    ]
                      .filter(Boolean)
                      .join(" · ") || undefined
                  : undefined;
              const frontier = tab === "actions" && frontierIds.includes(id);
              return (
                <HandCard
                  key={`${tab}-${id}-${index}`}
                  tab={tab as CardTab}
                  id={id}
                  frontier={frontier}
                  reaction={!frontier && reactionIds.has(`${tab}:${id}`)}
                  discardable={mustDiscard > 0 && tab === "actions" && !frontier}
                  play={
                    frontier
                      ? frontierPlayability?.[id]
                      : tab === "actions"
                        ? playability?.[id]
                        : tab === "notes"
                          ? notePlayability?.[id]
                          : relic
                  }
                  relicTag={relicTag}
                  passive={passive}
                  onPlay={() => {
                    // Ta sama ścieżka co upuszczenie na strefę zagrania / stos odrzuconych.
                    playUi("drop");
                    if (mustDiscard > 0 && tab === "actions" && !frontier) {
                      void discardCard(id);
                      return;
                    }
                    setPlayingCard({ id, tab, frontier });
                  }}
                  onDragChange={(cardId) => {
                    setDragCard(
                      cardId === null
                        ? null
                        : {
                            id: cardId,
                            tab,
                            frontier,
                            discard: mustDiscard > 0 && tab === "actions" && !frontier,
                          },
                    );
                    if (cardId === null) setZoneOver(false);
                  }}
                />
              );
            })
          )}
        </div>
      )}
      </div>
      )}
      {/* Limit ręki: plakietka NAD dokiem (nie zmienia jego wysokości). */}
      {mustDiscard > 0 && (
        <div className={styles.discardBanner} role="status">
          <IconTrash size={14} aria-hidden="true" />
          <span>
            Hand limit {handLimit?.handLimit ?? 7}: drag {mustDiscard} action card
            {mustDiscard === 1 ? "" : "s"} onto the discard pile.
          </span>
          {discardError && <b className={styles.discardError}>{discardError}</b>}
        </div>
      )}
    </section>

    <HeldPlayBanner
      viewerId={active.discordId ?? null}
      onNeedHand={() => {
        setOpen(true);
        setTab("actions");
      }}
    />
    <ReactionPauseBanner
      viewerId={active.discordId ?? null}
      onNeedHand={() => {
        setOpen(true);
        setTab("actions");
      }}
    />

    {/* Strefa zagrania - poza <section>, bo transform doku zmieniłby pozycję `fixed`. */}
    {dragCard && (
      <div
        className={styles.dropZone}
        data-over={zoneOver || undefined}
        data-discard={dragCard.discard || undefined}
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
          setZoneOver(true);
        }}
        onDragLeave={() => setZoneOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          const dragged = dragCard;
          setZoneOver(false);
          setDragCard(null);
          if (!dragged) return;
          playUi("drop");
          if (dragged.discard) {
            const discarded = e.dataTransfer.getData("text/x-actioncard") || dragged.id;
            void discardCard(discarded);
            return;
          }
          const type = dragged.frontier
            ? FRONTIER_DRAG_TYPE
            : (DRAG_TYPE[dragged.tab] ?? "text/x-actioncard");
          const cardId = e.dataTransfer.getData(type);
          if (cardId) {
            setPlayingCard({
              id: cardId,
              tab: dragged.tab,
              frontier: dragged.frontier,
            });
          }
        }}
      >
        <span className={styles.dropLabel}>
        {dragCard.discard ? (
          <IconTrash size={18} aria-hidden="true" />
        ) : (
          <IconPlayerPlayFilled size={18} aria-hidden="true" />
        )}
        <span>
          {dragCard.discard
            ? "Drop to discard"
            : `Drop to ${dragCard.tab === "relics" ? "use" : "play"}`}{" "}
          {dragCard.tab === "relics"
            ? (getRelicData(dragCard.id)?.name ?? dragCard.id)
            : dragCard.tab === "notes"
              ? (getPromissoryNoteData(dragCard.id, noteColors)?.displayName || dragCard.id)
            : dragCard.frontier
              ? (getExploration(dragCard.id)?.name ?? dragCard.id)
              : (getActionCard(dragCard.id)?.name ?? dragCard.id)}
        </span>
        </span>
      </div>
    )}

    {playingCard && active.discordId && (
      <ActionCardPlayModal
        key={`${playingCard.tab}-${playingCard.id}`}
        kind={
          playingCard.frontier
            ? "frontier"
            : playingCard.tab === "relics"
              ? "relic"
              : playingCard.tab === "notes"
                ? "note"
                : "card"
        }
        cardId={playingCard.id}
        cardName={
          playingCard.tab === "relics"
            ? (getRelicData(playingCard.id)?.name ?? playingCard.id)
            : playingCard.tab === "notes"
              ? (getPromissoryNoteData(playingCard.id, noteColors)?.displayName || playingCard.id)
            : playingCard.frontier
              ? (getExploration(playingCard.id)?.name ?? playingCard.id)
              : (getActionCard(playingCard.id)?.name ?? playingCard.id)
        }
        playerId={active.discordId}
        seq={holdSeq ?? undefined}
        onClose={() => setPlayingCard(null)}
        onPlayed={() => setPlayingCard(null)}
      />
    )}
    </>
  );
}

export default BottomHandDock;
