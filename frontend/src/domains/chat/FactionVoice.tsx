import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { createPortal } from "react-dom";
import cx from "clsx";
import { IconMessageCircle2 } from "@tabler/icons-react";
import { ActionIcon, Button } from "@/ds";
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
import { quoted } from "@/entities/lore/typography";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { FactionIcon } from "@/shared/ui/FactionIcon";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import styles from "./FactionVoice.module.css";

/** Jak długo dymek z kwestią wisi nad polem gracza. */
export const BUBBLE_MS = 9000;

/**
 * Kolor gracza jako trójka „r g b”: `--pc` dla przycisku i dymku, `--k` dla `DetailsCard`
 * (karta szczegółów barwi nim nagłówek i etykiety — jak każda inna karta w grze).
 */
function usePlayerTint(playerId: string): CSSProperties {
  const color = useGameData()?.playerData?.find((p) => p.discordId === playerId)?.color;
  const rgb = color ? resolvePrimaryRgb(color) : undefined;
  const triplet = rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "148 163 184";
  return { "--pc": triplet, "--k": triplet } as CSSProperties;
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

/** Odstęp dymka od pola gracza i od krawędzi okna (px ekranu). */
const GAP = 14;
const EDGE = 8;

/**
 * Ustawia dymek (position: fixed) przy elemencie `anchor`: nad nim, a gdy brak miejsca — pod nim;
 * w poziomie zawsze w oknie. Śledzi kotwicę co klatkę (mapa się przesuwa i skaluje), pisząc
 * styl wprost do DOM, bez re-renderów.
 */
function useFollowAnchor(
  active: boolean,
  anchor: RefObject<HTMLElement | null>,
  bubble: RefObject<HTMLElement | null>,
) {
  useLayoutEffect(() => {
    if (!active) return;
    let frame = 0;
    const place = () => {
      const a = anchor.current;
      const b = bubble.current;
      if (a && b) {
        const r = a.getBoundingClientRect();
        const w = b.offsetWidth;
        const h = b.offsetHeight;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const below = r.top - GAP - h < EDGE && r.bottom + GAP + h <= vh - EDGE;
        const cx = r.left + r.width / 2;
        const left = Math.min(Math.max(cx - w / 2, EDGE), Math.max(EDGE, vw - w - EDGE));
        const rawTop = below ? r.bottom + GAP : r.top - GAP - h;
        const top = Math.min(Math.max(rawTop, EDGE), Math.max(EDGE, vh - h - EDGE));
        b.style.left = `${left}px`;
        b.style.top = `${top}px`;
        b.dataset.side = below ? "below" : "above";
        // Ogonek celuje w środek pola, także gdy dymek dosunięto do krawędzi okna.
        const tail = Math.min(Math.max(cx - left, 20), w - 20);
        b.style.setProperty("--tail-x", `${tail}px`);
        b.style.visibility = "visible";
      }
      frame = window.requestAnimationFrame(place);
    };
    place();
    return () => window.cancelAnimationFrame(frame);
  }, [active, anchor, bubble]);
}

/**
 * DYMEK z kwestią przy głównym polu gracza (kółko z frakcją). Wstaw go W TYM polu: niewidoczna
 * kotwica bierze prostokąt rodzica, a sam dymek rysuje się w portalu na `body`, więc nigdy nie
 * jest ucięty przez krawędź mapy (nad polem, a przy górnej krawędzi okna — pod nim).
 * Wygląd = cytat frakcji z ekranu wyboru: szeryfowa kursywa + podpis frakcji w jej kolorze.
 */
export function FactionVoiceBubble({
  playerId,
  author,
}: {
  playerId: string;
  /** Podpis pod kwestią (nazwa frakcji). */
  author: string;
}) {
  const text = useLatestVoice(playerId);
  const tint = usePlayerTint(playerId);
  const marker = useRef<HTMLSpanElement | null>(null);
  const anchor = useRef<HTMLElement | null>(null);
  const bubble = useRef<HTMLElement | null>(null);
  useLayoutEffect(() => {
    anchor.current = marker.current?.parentElement ?? null;
  });
  useFollowAnchor(!!text, anchor, bubble);

  return (
    <>
      <span ref={marker} hidden />
      {text &&
        createPortal(
          <figure
            ref={bubble}
            className={styles.bubble}
            style={{ ...tint, visibility: "hidden" }}
            role="status"
            aria-label="Faction voice line"
          >
            <blockquote className={styles.quote}>{quoted(text)}</blockquote>
            <figcaption className={styles.author}>{author}</figcaption>
          </figure>,
          document.body,
        )}
    </>
  );
}

/**
 * KOMUNIKATY FRAKCJI: przycisk przy polu własnego gracza otwiera kartę z jednakowymi kategoriami
 * (`entities/lore/factionVoiceLines.ts`, kwestie wpisuje użytkownik). Klik wysyła losową kwestię
 * kategorii przez czat jako publiczną wiadomość z flagą `voice`; dymek widzą wszyscy
 * (`FactionVoiceBubble`). Niczego nie zmienia w regułach. U cudzych graczy nic się nie renderuje.
 *
 * `variant="map"` = okrągły żeton w rzędzie punktów w głównym polu na planszy; `"header"` = mała ikona
 * w nagłówku panelu gracza.
 */
export function FactionVoice({
  playerId,
  faction,
  factionName,
  variant = "header",
  className,
}: {
  playerId: string;
  faction: string;
  /** Pełna nazwa frakcji do nagłówka karty; domyślnie id. */
  factionName?: string;
  variant?: "map" | "header";
  className?: string;
}) {
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

  const onMap = variant === "map";

  return (
    <SmoothPopover opened={opened} onChange={setOpened} position={onMap ? "right" : "bottom"}>
      <SmoothPopover.Target>
        <ActionIcon
          variant={onMap ? "default" : "subtle"}
          size={onMap ? 34 : 28}
          radius="50%"
          className={cx(onMap && styles.mapTrigger, className)}
          style={tint}
          aria-label="Faction voice lines"
          aria-expanded={opened}
          title="Say something"
          onClick={() => setOpened((o) => !o)}
        >
          <IconMessageCircle2 size={onMap ? 19 : 18} stroke={1.8} aria-hidden="true" />
        </ActionIcon>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown>
        <DetailsCard width={300} style={tint}>
          <DetailsCard.Title
            icon={<FactionIcon faction={faction} w={40} h={40} fit="contain" alt="" />}
            title="Say something"
            type={factionName ?? faction}
            meta={["Seen by all players"]}
          />
          <div className={styles.grid}>
            {VOICE_CATEGORIES.map(({ id, label }) => {
              const empty = voiceLinesFor(faction, id).length === 0;
              return (
                <Button
                  key={id}
                  variant="default"
                  size="sm"
                  fullWidth
                  disabled={busy || empty}
                  title={empty ? "No lines yet" : undefined}
                  onClick={() => say(id)}
                >
                  {label}
                </Button>
              );
            })}
          </div>
        </DetailsCard>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
