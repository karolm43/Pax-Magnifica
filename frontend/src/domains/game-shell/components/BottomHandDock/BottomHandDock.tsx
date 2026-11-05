import { useMemo, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import cx from "clsx";
import {
  IconCards,
  IconChevronDown,
  IconLayoutGrid,
  IconTarget,
  IconTicket,
} from "@tabler/icons-react";
import { UnstyledButton } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameData } from "@/state/useGameContext";
import { useFactionColors } from "@/hooks/useFactionColors";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { ActionCardDetailsCard } from "@/domains/cards/components/ActionCardDetailsCard";
import { SecretObjectiveCard } from "@/domains/cards/components/SecretObjectiveCard";
import { PromissoryNoteCard } from "@/domains/cards/components/PromissoryNoteCard";
import { usePlayerHand } from "@/domains/game-shell/components/SecretHand/usePlayerHand";
import {
  loadStoredChoice,
  saveStoredChoice,
} from "@/utils/localStorageSettings";
import type { PlayerData } from "@/entities/data/types";
import styles from "./BottomHandDock.module.css";

/**
 * „Pasek ręki" aktywnego gracza u dołu mapy — styl stołu (TTS): karty leżą
 * wachlarzem jako kafelki z rewersem i nazwą, kliknięcie odsłania pełną kartę
 * (treść + grafika rewersu). Trzy kategorie jako segmenty z licznikami: karty
 * akcji, tajne cele i promissory notes (weksle). Rękę bierze z endpointu
 * ``/game/{id}/hand`` (usePlayerHand z pominięciem bramki — tryb lokalny,
 * operator widzi wszystko), który zwraca rękę AKTYWNEGO gracza.
 *
 * To czysta nakładka informacyjno-podglądowa (nie wykonuje akcji): pokazuje, co
 * gracz trzyma w ręce, dokładnie jak przy fizycznym stole.
 */

type HandTab = "actions" | "secrets" | "notes";

const TABS: {
  key: HandTab;
  label: string;
  tone: string;
  icon: typeof IconCards;
}[] = [
  { key: "actions", label: "Action cards", tone: "239, 68, 68", icon: IconCards },
  { key: "secrets", label: "Secrets", tone: "239, 68, 68", icon: IconTarget },
  { key: "notes", label: "Notes", tone: "6, 182, 212", icon: IconTicket },
];

const BACKS: Record<HandTab, string> = {
  actions: assetUrl("/player_area/cardback_action.jpg"),
  secrets: assetUrl("/player_area/cardback_secret.jpg"),
  notes: assetUrl("/player_area/pa_cardbacks_pn.png"),
};

const EMPTY_COPY: Record<HandTab, string> = {
  actions: "No action cards in hand",
  secrets: "No secret objectives in hand",
  notes: "No promissory notes in hand",
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

/** Nazwa/etykieta karty wg kategorii (z wbudowanych danych AsyncTI4). */
function useCardLabel(tab: HandTab, id: string): { name: string; tag?: string } {
  const factionColorMap = useFactionColors();
  if (tab === "actions") {
    const card = getActionCard(id);
    return { name: card?.name ?? id, tag: card?.window };
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
    name: note?.noteData.shortName || note?.displayName || id,
    tag: note?.faction,
  };
}

/** Pełna karta (treść + grafika) do odsłonięcia w popoverze po kliknięciu. */
function CardDetails({ tab, id }: { tab: HandTab; id: string }) {
  if (tab === "actions") return <ActionCardDetailsCard actionCardId={id} />;
  if (tab === "secrets") return <SecretObjectiveCard secretId={id} />;
  return <PromissoryNoteCard promissoryNoteId={id} />;
}

/** Jeden kafelek karty w wachlarzu: rewers + nazwa + znacznik; klik = podgląd. */
function HandCard({ tab, id }: { tab: HandTab; id: string }) {
  const [open, setOpen] = useState(false);
  const { name, tag } = useCardLabel(tab, id);
  const tone = TABS.find((t) => t.key === tab)?.tone ?? "148, 163, 184";
  return (
    <SmoothPopover opened={open} onChange={setOpen} position="top">
      <SmoothPopover.Target>
        <button
          type="button"
          className={styles.card}
          style={{ "--hk": tone } as CSSProperties}
          data-open={open || undefined}
          onClick={() => setOpen((v) => !v)}
          title={name}
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
        <CardDetails tab={tab} id={id} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

export function BottomHandDock() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const gameData = useGameData();
  const playerData = gameData?.playerData ?? [];
  const active: PlayerData | undefined = playerData.find((p) => p.active);

  const { data: hand } = usePlayerHand(gameId, { ignoreAuthGate: true });
  const [open, setOpen] = useDockOpen();
  const [tab, setTab] = useState<HandTab>("actions");

  const counts = useMemo(
    () => ({
      actions: hand?.actionCards.length ?? 0,
      secrets: hand?.secretObjectives.length ?? 0,
      notes: hand?.promissoryNotes.length ?? 0,
    }),
    [hand],
  );

  const ids = useMemo(() => {
    if (!hand) return [] as string[];
    if (tab === "actions") return hand.actionCards;
    if (tab === "secrets") return hand.secretObjectives;
    return hand.promissoryNotes;
  }, [hand, tab]);

  // Dock pojawia się tylko, gdy jest aktywny gracz (jego rękę pokazujemy).
  if (!active) return null;

  return (
    <section
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
                onClick={() => setTab(t.key)}
              >
                <Icon size={14} aria-hidden="true" />
                <span className={styles.tabLabel}>{t.label}</span>
                <b className={styles.tabCount}>{counts[t.key]}</b>
              </button>
            );
          })}
        </div>

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

      {open && (
        <div className={styles.fan} role="tabpanel">
          {ids.length === 0 ? (
            <p className={styles.empty}>
              <IconLayoutGrid size={14} aria-hidden="true" />
              {EMPTY_COPY[tab]}
            </p>
          ) : (
            ids.map((id, index) => (
              <HandCard key={`${tab}-${id}-${index}`} tab={tab} id={id} />
            ))
          )}
        </div>
      )}
    </section>
  );
}

export default BottomHandDock;
