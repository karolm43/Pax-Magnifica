import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import cx from "clsx";
import {
  IconCards,
  IconChevronDown,
  IconCpu,
  IconDiamond,
  IconLayoutGrid,
  IconPlayerPlayFilled,
  IconTarget,
  IconTrash,
  IconTicket,
} from "@tabler/icons-react";
import { UnstyledButton } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { useFactionColors } from "@/hooks/useFactionColors";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getAgenda } from "@/entities/lookup/agendas";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { getRelicData } from "@/entities/lookup/relics";
import { getExploration } from "@/entities/lookup/explorations";
import { RelicCard } from "@/domains/player/components/Relic/RelicCard";
import { Tech } from "@/domains/player/components/Tech";
import { ActionCardDetailsCard } from "@/domains/cards/components/ActionCardDetailsCard";
import { SecretObjectiveCard } from "@/domains/cards/components/SecretObjectiveCard";
import { PromissoryNoteCard } from "@/domains/cards/components/PromissoryNoteCard";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import { getOwnerRgb } from "@/domains/player/components/PromissoryNote";
import {
  loadStoredChoice,
  saveStoredChoice,
} from "@/utils/localStorageSettings";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import type { PlayerData } from "@/entities/data/types";
import { HoldControls } from "./HoldControls";
import { HeldPlayBanner } from "./HeldPlayBanner";
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

type HandTab = "actions" | "secrets" | "notes" | "relics" | "techs";

/** Zakładki z kartami w wachlarzu (technologie mają własny widok kafelków). */
type CardTab = Exclude<HandTab, "techs">;

/** Minimalny kształt decyzji silnika o zagrywalności (karta akcji albo relikt). */
type PlayInfo = { playable: boolean; reason: string | null };

const TABS: {
  key: HandTab;
  label: string;
  tone: string;
  icon: typeof IconCards;
}[] = [
  { key: "actions", label: "Action cards", tone: "239, 68, 68", icon: IconCards },
  { key: "secrets", label: "Secrets", tone: "239, 68, 68", icon: IconTarget },
  { key: "notes", label: "Notes", tone: "6, 182, 212", icon: IconTicket },
  { key: "relics", label: "Relics", tone: "234, 179, 8", icon: IconDiamond },
  { key: "techs", label: "Techs", tone: "110, 168, 255", icon: IconCpu },
];

const BACKS: Record<CardTab, string> = {
  actions: assetUrl("/player_area/cardback_action.jpg"),
  secrets: assetUrl("/player_area/cardback_secret.jpg"),
  notes: assetUrl("/player_area/pa_cardbacks_pn.png"),
  relics: assetUrl("/player_area/cardback_relic.jpg"),
};

const EMPTY_COPY: Record<HandTab, string> = {
  actions: "No action cards in hand",
  secrets: "No secret objectives in hand",
  notes: "No promissory notes in hand",
  relics: "No relics in play",
  techs: "No technologies",
};

/** Karty, które można przeciągnąć na strefę zagrania (karta akcji albo relikt z ACTION). */
const PLAYABLE_TABS: ReadonlySet<HandTab> = new Set(["actions", "relics", "notes"]);

/** Typ przeciąganego elementu w `dataTransfer` (strefa zagrania rozróżnia kartę i relikt). */
const DRAG_TYPE: Partial<Record<HandTab, string>> = {
  actions: "text/x-actioncard",
  relics: "text/x-relic",
  notes: "text/x-promissory",
};

/** Typ przeciąganej karty frontier (Enigmatic Device) w `dataTransfer`. */
const FRONTIER_DRAG_TYPE = "text/x-frontier";

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
 * Czy jest otwarte okno pełnoekranowe (walka, inwazja, agenda, produkcja, technologie,
 * eksploracja — atrybut `data-fullscreen-overlay` na ich korzeniu). Dok leży NAD nimi
 * (karty reakcji, RULES.md 53.5), więc rozwinięty zasłaniał dół okna (np. tabele jednostek).
 */
function useFullscreenOverlay(): boolean {
  const [present, setPresent] = useState(false);
  useEffect(() => {
    const check = () =>
      setPresent(document.querySelector("[data-fullscreen-overlay]") !== null);
    check();
    const observer = new MutationObserver(check);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);
  return present;
}

/** Nazwa/etykieta karty wg kategorii (z wbudowanych danych AsyncTI4). */
function useCardLabel(
  tab: CardTab,
  id: string,
  /** Tylko relikty: znacznik z decyzji silnika (rodzaj + wyczerpanie). */
  relicTag?: string,
  /** Karta frontier (Enigmatic Device) leżąca w zakładce Action cards. */
  frontier?: boolean,
): { name: string; tag?: string; ownerRgb?: string } {
  const factionColorMap = useFactionColors();
  if (tab === "actions" && frontier) {
    return { name: getExploration(id)?.name ?? id, tag: "Frontier · Action" };
  }
  if (tab === "actions") {
    const card = getActionCard(id);
    return { name: card?.name ?? id, tag: card?.window };
  }
  if (tab === "relics") {
    return { name: getRelicData(id)?.name ?? id, tag: relicTag };
  }
  if (tab === "secrets") {
    const secret = getSecretObjectiveData(id);
    return {
      name: secret?.name ?? id,
      tag: secret ? `${secret.points} VP` : undefined,
    };
  }
  const note = getPromissoryNoteData(id, factionColorMap);
  return {
    name: note?.displayName || id,
    tag: note?.faction,
    // Nota w kolorze gracza, do którego należy (także gdy leży w cudzej ręce).
    ownerRgb: note
      ? getOwnerRgb(note.faction, note.color, factionColorMap)
      : undefined,
  };
}

/** Pełna karta (treść + grafika) do odsłonięcia w popoverze po kliknięciu. */
function CardDetails({
  tab,
  id,
  frontier,
}: {
  tab: CardTab;
  id: string;
  frontier?: boolean;
}) {
  if (tab === "actions" && frontier) {
    const card = getExploration(id);
    return (
      <div style={{ maxWidth: 320, padding: 14, whiteSpace: "pre-line" }}>
        <b>{card?.name ?? id}</b>
        <p style={{ margin: "8px 0 0" }}>{card?.text ?? ""}</p>
      </div>
    );
  }
  if (tab === "actions") return <ActionCardDetailsCard actionCardId={id} />;
  if (tab === "secrets") return <SecretObjectiveCard secretId={id} />;
  if (tab === "relics") return <RelicCard relicId={id} />;
  return <PromissoryNoteCard promissoryNoteId={id} />;
}

/** Jeden kafelek karty w wachlarzu: rewers + nazwa + znacznik; klik = podgląd, drag = zagranie. */
function HandCard({
  tab,
  id,
  play,
  relicTag,
  passive,
  frontier,
  reaction,
  discardable,
  onDragChange,
}: {
  tab: CardTab;
  id: string;
  /** Ręka ponad limitem (R_action_cards): kartę akcji przeciąga się na stos odrzuconych. */
  discardable?: boolean;
  /** Karta frontier w zakładce Action cards (przeciągana jak karta akcji). */
  frontier?: boolean;
  /** Decyzja silnika o zagrywalności (karty akcji i relikty z ACTION); brak = jeszcze nie wiadomo. */
  play?: PlayInfo;
  /** Relikt: znacznik rodzaju/wyczerpania pod nazwą. */
  relicTag?: string;
  /** Relikt pasywny: działa sam, nie ma co zagrywać (nie przyciemniamy go jak zablokowanej karty). */
  passive?: boolean;
  /** Okno reakcji tej karty jest otwarte TERAZ (RULES.md 54.8) - karta miga. */
  reaction?: boolean;
  onDragChange: (cardId: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const { name, tag, ownerRgb } = useCardLabel(tab, id, relicTag, frontier);
  const playableTab = PLAYABLE_TABS.has(tab);
  const canDrag = discardable === true || (playableTab && play?.playable === true);
  const locked =
    !discardable && playableTab && !passive && play !== undefined && !play.playable;
  const hint = discardable
    ? `${name} - drag onto the discard pile to discard it (hand limit)`
    : canDrag
    ? reaction
      ? `${name} - its window is open now: drag onto the play zone to play`
      : `${name} - drag onto the play zone to play`
    : locked
      ? `${name} - can't be played now: ${play?.reason ?? "not available"}`
      : passive
        ? `${name} - passive, works on its own`
        : name;
  const tone =
    ownerRgb ?? TABS.find((t) => t.key === tab)?.tone ?? "148, 163, 184";
  return (
    // Wrapper (nie sam <button>) jest elementem przeciąganym: Firefox nie przeciąga przycisków.
    <div
      className={styles.cardWrap}
      draggable={canDrag}
      onDragStart={(e) => {
        if (!canDrag) {
          e.preventDefault();
          return;
        }
        e.dataTransfer.setData(
          frontier ? FRONTIER_DRAG_TYPE : (DRAG_TYPE[tab] ?? "text/x-actioncard"),
          id,
        );
        e.dataTransfer.effectAllowed = "move";
        setOpen(false);
        onDragChange(id);
      }}
      onDragEnd={() => onDragChange(null)}
    >
    <SmoothPopover opened={open} onChange={setOpen} position="top">
      <SmoothPopover.Target>
        <button
          type="button"
          className={styles.card}
          style={{ "--hk": tone } as CSSProperties}
          data-open={open || undefined}
          data-tinted={ownerRgb ? true : undefined}
          data-playable={canDrag || undefined}
          data-discard={discardable || undefined}
          data-reaction={(canDrag && reaction) || undefined}
          data-locked={locked || undefined}
          onClick={() => setOpen((v) => !v)}
          title={hint}
        >
          <span
            className={styles.cardArt}
            style={{ backgroundImage: `url("${BACKS[tab]}")` }}
            aria-hidden="true"
          />
          <span className={styles.cardMeta}>
            <b className={styles.cardName}>{name}</b>
            {tag && <small className={styles.cardTag}>{tag}</small>}
          </span>
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <CardDetails tab={tab} id={id} frontier={frontier} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
    </div>
  );
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
  // Przy oknie pełnoekranowym dok startuje ZWINIĘTY; rozwinięcie w tym czasie jest chwilowe
  // (`peek`) i nie nadpisuje zapamiętanego wyboru gracza.
  const overlayOpen = useFullscreenOverlay();
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

  // Prywatne podglądy z kart reakcji: Insider Information (top agend) i Extreme Duress (tajne cele).
  const peekLines = useMemo(() => {
    const lines: string[] = [];
    if (hand?.agendaPeek?.length) {
      const names = hand.agendaPeek.map((id) => getAgenda(id)?.name ?? id);
      lines.push(`Top of the agenda deck: ${names.join(" · ")}`);
    }
    for (const [owner, ids] of Object.entries(hand?.revealedSecrets ?? {})) {
      const names = ids.map((id) => getSecretObjectiveData(id)?.name ?? id);
      lines.push(`Secret objectives of ${owner}: ${names.join(" · ") || "none"}`);
    }
    return lines;
  }, [hand?.agendaPeek, hand?.revealedSecrets]);

  // Mierzymy wysokość doku (zwinięty / rozwinięty) i wystawiamy ją jako zmienną CSS
  // ``--hand-dock-clear`` na <html> - pastylki powrotu do okien (produkcja, technologie…)
  // ustawiają się NAD dokiem, także gdy wachlarz kart jest otwarty.
  const [dockNode, setDockNode] = useState<HTMLElement | null>(null);
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

        {active.discordId && <HoldControls playerId={active.discordId} />}

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

      {open && peekLines.length > 0 && (
        <ul className={styles.peek} aria-label="Cards you were shown">
          {peekLines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}

      {/* Fragmenty -> relikt (RULES.md 59.7): przycisk „Forge relic" nad reliktami. */}
      {open && tab === "relics" && active.discordId && (
        <RelicForgePanel playerId={active.discordId} enabled />
      )}

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

      {open && tab === "techs" && <TechFan player={active} />}

      {open && tab !== "techs" && (
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
    </section>

    <HeldPlayBanner
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
