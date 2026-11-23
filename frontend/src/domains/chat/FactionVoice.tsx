import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { IconMessageCircle2 } from "@tabler/icons-react";
import { useBoardEditor, useActivityFeed, useChat } from "@/api/useBoardEditor";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { humanHandOwners } from "@/domains/offers/handReactions";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { useGameData } from "@/state/useGameContext";
import {
  pickVoiceLine,
  voiceLinesFor,
  VOICE_CATEGORIES,
  type VoiceCategoryId,
} from "@/entities/lore/factionVoiceLines";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import styles from "./FactionVoice.module.css";

/** Jak długo dymek z kwestią wisi nad nazwą frakcji. */
export const BUBBLE_MS = 9000;

/** Kolor gracza jako trójka „r g b” do `rgb(var(--pc) / a)` — przycisk, panel i dymek w jego barwie. */
function usePlayerTint(playerId: string): CSSProperties {
  const color = useGameData()?.playerData?.find((p) => p.discordId === playerId)?.color;
  const rgb = color ? resolvePrimaryRgb(color) : undefined;
  return { "--pc": rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "148 163 184" } as CSSProperties;
}

/** Id gracza, który siedzi przy tym ekranie (w sieci z tokenu). */
function useMe(): string | null {
  const { data: networkMe } = useNetworkMe();
  const { data: feed } = useActivityFeed();
  return humanHandOwners(networkMe, feed?.players)[0] ?? null;
}

/**
 * Najnowsza NOWA kwestia nadawcy (`voice`) na czas `BUBBLE_MS`. Kwestie sprzed wejścia na stronę
 * (przeładowanie) nie wyskakują jako nowe.
 */
function useLatestVoice(playerId: string): string | null {
  const { data: messages } = useChat(useMe());
  const [shown, setShown] = useState<{ seq: number; text: string } | null>(null);
  const baseline = useRef<number | null>(null);
  const latest = messages?.filter((m) => m.voice && m.sender === playerId && m.text != null).at(-1);

  useEffect(() => {
    if (!messages) return;
    if (baseline.current === null) {
      baseline.current = latest?.seq ?? 0;
      return;
    }
    if (!latest || latest.seq <= baseline.current) return;
    baseline.current = latest.seq;
    setShown({ seq: latest.seq, text: latest.text ?? "" });
  }, [messages, latest]);

  // Osobny timer: odświeżenie czatu nie może go skasować ani zostawić dymka na stałe.
  const shownSeq = shown?.seq;
  useEffect(() => {
    if (shownSeq === undefined) return;
    const timer = window.setTimeout(() => setShown(null), BUBBLE_MS);
    return () => window.clearTimeout(timer);
  }, [shownSeq]);

  return shown?.text ?? null;
}

/**
 * DYMEK z kwestią: wychodzi z NAZWY FRAKCJI w polu gracza. Wstaw go obok nazwy; sam rysuje się
 * w portalu na `body` (nad całą planszą i oknami), przypięty nad nazwą.
 */
export function FactionVoiceBubble({ playerId }: { playerId: string }) {
  const text = useLatestVoice(playerId);
  const tint = usePlayerTint(playerId);
  const anchor = useRef<HTMLSpanElement | null>(null);
  const [pos, setPos] = useState<{ left: number; bottom: number } | null>(null);

  useLayoutEffect(() => {
    if (!text || !anchor.current) {
      setPos(null);
      return;
    }
    const rect = anchor.current.parentElement?.getBoundingClientRect() ?? anchor.current.getBoundingClientRect();
    setPos({ left: rect.left + rect.width / 2, bottom: window.innerHeight - rect.top + 10 });
  }, [text]);

  return (
    <>
      <span ref={anchor} aria-hidden="true" />
      {text &&
        pos &&
        createPortal(
          <div
            className={styles.bubble}
            style={{ ...tint, left: pos.left, bottom: pos.bottom }}
            role="status"
            aria-label="Faction voice line"
          >
            <div className={styles.bubbleInner}>“{text}”</div>
          </div>,
          document.body,
        )}
    </>
  );
}

/**
 * KOMUNIKATY FRAKCJI: przycisk w polu własnego gracza otwiera 9 jednakowych kategorii
 * (`entities/lore/factionVoiceLines.ts`, kwestie wpisuje użytkownik). Klik wysyła losową kwestię
 * kategorii przez czat jako publiczną wiadomość z flagą `voice`; dymek widzą wszyscy
 * (`FactionVoiceBubble`). Niczego nie zmienia w regułach. U cudzych graczy nic się nie renderuje.
 */
export function FactionVoice({ playerId, faction }: { playerId: string; faction: string }) {
  const me = useMe();
  const { sendChat } = useBoardEditor();
  const [opened, setOpened] = useState(false);
  const [busy, setBusy] = useState(false);
  const tint = usePlayerTint(playerId);
  if (me !== playerId) return null;

  const say = (category: VoiceCategoryId) => {
    const text = pickVoiceLine(faction, category);
    if (busy || !text) return;
    setBusy(true);
    void sendChat(playerId, text, null, true)
      .then(() => setOpened(false))
      .catch(() => undefined) // powód pokazuje już useBoardEditor.post
      .finally(() => setBusy(false));
  };

  return (
    <span className={styles.wrap} style={tint}>
      <SmoothPopover opened={opened} onChange={setOpened} position="bottom">
        <SmoothPopover.Target>
          <button
            type="button"
            className={styles.btn}
            aria-label="Faction voice lines"
            aria-expanded={opened}
            title="Say something"
            onClick={() => setOpened((o) => !o)}
          >
            <IconMessageCircle2 size={22} stroke={1.8} aria-hidden="true" />
          </button>
        </SmoothPopover.Target>
        <SmoothPopover.Dropdown p={0}>
          <div className={styles.list} style={tint}>
            <div className={styles.head}>Say as your faction</div>
            <div className={styles.grid}>
              {VOICE_CATEGORIES.map(({ id, label }) => {
                const empty = voiceLinesFor(faction, id).length === 0;
                return (
                  <button
                    key={id}
                    type="button"
                    className={styles.cat}
                    disabled={busy || empty}
                    title={empty ? "No lines yet" : undefined}
                    onClick={() => say(id)}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </SmoothPopover.Dropdown>
      </SmoothPopover>
    </span>
  );
}
