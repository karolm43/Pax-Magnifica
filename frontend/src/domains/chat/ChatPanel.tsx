import { useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { IconLock, IconMessageCircle, IconMinus, IconSend } from "@tabler/icons-react";
import { useBoardEditor, useActivityFeed, useChat, type ChatMessage } from "@/api/useBoardEditor";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { humanHandOwners } from "@/domains/offers/handReactions";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { useGameData } from "@/state/useGameContext";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { PlayerTag } from "@/shared/ui/PlayerTag/PlayerTag";
import { playerName, playerRgb } from "@/domains/strategy/PlayerChip";
import styles from "./ChatPanel.module.css";

/*
 * CZAT PRZY STOLE (RULES.md 47.6, decyzja użytkownika 2026-11-17). Nieinwazyjny: zwinięty to mała
 * okrągła ikonka z licznikiem nieprzeczytanych; rozwinięty - przesuwalny panel (useDraggablePanel).
 * Szept (whisper): wybierasz gracza nad polem tekstu. Treść widzi tylko adresat, ale WSZYSCY widzą,
 * że szepczesz („X whispers to Y”) - to robi backend (``core/chat.py``), UI tylko wyświetla.
 */

const SEEN_KEY = "chat:lastSeen";

function readSeen(): number {
  try {
    return Number(localStorage.getItem(SEEN_KEY) ?? 0) || 0;
  } catch {
    return 0;
  }
}

function writeSeen(seq: number): void {
  try {
    localStorage.setItem(SEEN_KEY, String(seq));
  } catch {
    /* niedostępny localStorage - licznik po prostu nie przeżyje przeładowania */
  }
}

function clock(at: number): string {
  const d = new Date(at * 1000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function Line({ m, me }: { m: ChatMessage; me: string | null }) {
  const mine = m.sender === me;
  const toMe = m.to != null && m.to === me;
  return (
    <li
      className={styles.line}
      data-whisper={m.whisper || undefined}
      data-hidden={m.text == null || undefined}
      data-mine={mine || undefined}
      data-to-me={toMe || undefined}
      data-voice={m.voice || undefined}
    >
      <span className={styles.meta}>
        <time className={styles.time} title={new Date(m.at * 1000).toLocaleString()}>
          {clock(m.at)}
        </time>
        <PlayerTag playerId={m.sender} size={14} />
        {m.whisper && m.to && (
          <span className={styles.whisperTo}>
            <IconLock size={11} aria-hidden="true" />
            {m.text == null ? "whispers to" : "to"}
            <PlayerTag playerId={m.to} size={14} />
          </span>
        )}
      </span>
      {m.text != null && <span className={styles.text}>{m.text}</span>}
    </li>
  );
}

export function ChatPanel() {
  const gameData = useGameData();
  const { data: networkMe } = useNetworkMe();
  const { data: feed } = useActivityFeed();
  const me = humanHandOwners(networkMe, feed?.players)[0] ?? null;
  const { data: messages = [] } = useChat(me);
  const { sendChat } = useBoardEditor();
  const drag = useDraggablePanel("panel:chat");
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [to, setTo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [seen, setSeen] = useState(readSeen);
  const listRef = useRef<HTMLOListElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const players = useMemo(
    () =>
      (gameData?.playerData ?? []).filter(
        (p) => p.faction && p.faction !== "neutral" && p.discordId,
      ),
    [gameData?.playerData],
  );
  const others = players.filter((p) => p.discordId !== me);
  const lastSeq = messages.length ? messages[messages.length - 1].seq : 0;
  // Nowa gra zaczyna dziennik od 1 - stary licznik „przeczytanych” nie może go zagłuszyć.
  const seenSeq = seen > lastSeq ? 0 : seen;
  const unread = messages.filter((m) => m.seq > seenSeq && m.sender !== me);
  const whisperForMe = unread.some((m) => m.to != null && m.to === me);

  // Otwarty panel = wszystko przeczytane; przewijamy na dół przy nowej wiadomości.
  useEffect(() => {
    if (!open) return;
    if (lastSeq !== seen) {
      setSeen(lastSeq);
      writeSeen(lastSeq);
    }
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [open, lastSeq, seen]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open, to]);

  if (players.length === 0) return null;

  const send = () => {
    const body = text.trim();
    if (!me || !body || busy) return;
    setBusy(true);
    void sendChat(me, body, to)
      .then(() => setText(""))
      .catch(() => undefined) // powód pokazuje już useBoardEditor.post
      .finally(() => setBusy(false));
  };
  const onKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      send();
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };
  const target = others.find((p) => p.discordId === to) ?? null;

  if (!open) {
    return createPortal(
      <button
        type="button"
        className={styles.launcher}
        data-alert={whisperForMe || undefined}
        onClick={() => setOpen(true)}
        aria-label={unread.length ? `Open chat (${unread.length} unread)` : "Open chat"}
        title="Chat"
      >
        <IconMessageCircle size={18} aria-hidden="true" />
        {unread.length > 0 && <span className={styles.badge}>{unread.length}</span>}
      </button>,
      document.body,
    );
  }

  return createPortal(
    <section
      className={styles.panel}
      aria-label="Chat"
      ref={drag.ref}
      style={drag.style}
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
    >
      <header
        className={styles.head}
        data-grab
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move · double-click resets position"
      >
        <IconMessageCircle size={15} aria-hidden="true" />
        <span className={styles.title}>Chat</span>
        <button
          type="button"
          className={styles.close}
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => setOpen(false)}
          aria-label="Minimize chat"
          title="Minimize (Esc)"
        >
          <IconMinus size={15} aria-hidden="true" />
        </button>
      </header>

      <ol className={styles.list} ref={listRef} aria-live="polite">
        {messages.length === 0 ? (
          <li className={styles.empty}>No messages yet. Say hello, or whisper a deal.</li>
        ) : (
          messages.map((m) => <Line key={m.seq} m={m} me={me} />)
        )}
      </ol>

      {me ? (
        <div className={styles.compose}>
          <div className={styles.targets} role="group" aria-label="Send to">
            <button
              type="button"
              className={styles.target}
              aria-pressed={to == null}
              data-on={to == null || undefined}
              onClick={() => setTo(null)}
              title="Everyone sees the message"
            >
              All
            </button>
            {others.map((p) => (
              <button
                key={p.discordId}
                type="button"
                className={styles.target}
                aria-pressed={to === p.discordId}
                aria-label={`Whisper to ${playerName(p)}`}
                data-on={to === p.discordId || undefined}
                style={{ "--pc": playerRgb(p.color) } as CSSProperties}
                onClick={() => setTo(to === p.discordId ? null : p.discordId)}
                title={`Whisper to ${playerName(p)} — others see that you whisper, not what`}
              >
                {p.faction ? <CircularFactionIcon faction={p.faction} size={20} /> : playerName(p)}
              </button>
            ))}
          </div>
          {target && (
            <div className={styles.whisperHint}>
              <IconLock size={11} aria-hidden="true" /> Whisper to{" "}
              <PlayerTag playerId={target.discordId} size={13} /> — others see only that you
              whisper.
            </div>
          )}
          <div className={styles.inputRow}>
            <input
              ref={inputRef}
              className={styles.input}
              value={text}
              maxLength={500}
              placeholder={target ? `Whisper to ${playerName(target)}…` : "Message everyone…"}
              aria-label="Message"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKey}
            />
            <button
              type="button"
              className={styles.send}
              disabled={busy || !text.trim()}
              onClick={send}
              aria-label="Send"
            >
              <IconSend size={15} aria-hidden="true" />
            </button>
          </div>
        </div>
      ) : (
        <div className={styles.empty}>You are watching — only seated players can write.</div>
      )}
    </section>,
    document.body,
  );
}

export default ChatPanel;
