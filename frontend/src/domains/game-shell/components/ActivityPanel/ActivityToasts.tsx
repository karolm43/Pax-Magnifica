import { useEffect, useRef, useState, type CSSProperties } from "react";
import { IconChevronDown, IconX } from "@tabler/icons-react";
import { useActivityFeed, type ActivityEntry } from "@/api/useBoardEditor";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { describeActivity, type ActivityContext } from "./describeActivity";
import { activitySubject } from "./activitySubject";
import { hintFor } from "./Named";
import { useActivityContext } from "./useActivityContext";
import classes from "./ActivityToasts.module.css";

/** Ile powiadomień naraz; starsze ustępują nowym. */
const MAX_VISIBLE = 3;
/** Czas życia powiadomienia; najechanie kursorem wstrzymuje zamknięcie. */
const LIFETIME_MS = 8000;
/** Po zjechaniu kursorem powiadomienie zostaje jeszcze chwilę. */
const LINGER_MS = 2500;

/** Wpisy, które tylko szumią (zmiana tury widać na chipie tury). */
const SILENT_ACTIONS = new Set(["turn.next", "turn.end", "update"]);

/**
 * Czy wpis zasługuje na powiadomienie u tego widza: cudze akcje graczy (nie God-Mode,
 * nie zdarzenia bez sprawcy) oraz każda zdolność zastosowana automatycznie (także własna). Tryb lokalny nie zna „mnie" — pokazujemy tam akcje botów.
 */
export function shouldToast(
  entry: ActivityEntry,
  me: string | null,
  isBot: (id: string) => boolean,
  network: boolean,
): boolean {
  const a = entry.activity;
  if (a.kind === "godmode") return false;
  // Zdolność zastosowana automatycznie (Analytical, Brilliant): informujemy też jej właściciela.
  if (a.facts.some((f) => f.type === "ability_used")) return true;
  if (!a.actor_id || SILENT_ACTIONS.has(a.action)) return false;
  if (network) return a.actor_id !== me;
  return isBot(a.actor_id);
}

export function ToastCard({
  entry,
  ctx,
  onClose,
}: {
  entry: ActivityEntry;
  ctx: ActivityContext;
  onClose: () => void;
}) {
  const a = entry.activity;
  const view = describeActivity(a, ctx);
  const Icon = view.Icon;
  const actor = a.actor_id ? ctx.players[a.actor_id] : undefined;
  const subject = activitySubject(a);
  const hint = subject
    ? hintFor(subject.kind, subject.id, { idMap: ctx.strategyCardIdMap })
    : null;
  const hasDetails = view.facts.length > 0 || (hint !== null && hint.lines.length > 0);
  // Zwinięte = jedna linia „kto co zrobił”; po kliknięciu skutki + tekst karty/techu.
  const [open, setOpen] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  // Najświeższe ``onClose`` (nowa funkcja co render rodzica) bez restartu odliczania.
  const close = useRef(onClose);
  close.current = onClose;

  const arm = (ms: number) => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => close.current(), ms);
  };
  // Odliczanie startuje raz, przy pojawieniu się powiadomienia.
  useEffect(() => {
    timer.current = window.setTimeout(() => close.current(), LIFETIME_MS);
    return () => window.clearTimeout(timer.current);
  }, []);

  const toggle = () => {
    if (!hasDetails) return;
    // Rozwinięte czeka na gracza (czyta) — zamyka X albo ponowne zwinięcie.
    if (open) arm(LINGER_MS);
    else window.clearTimeout(timer.current);
    setOpen(!open);
  };

  return (
    <div
      className={classes.toast}
      role="status"
      data-open={open || undefined}
      data-clickable={hasDetails || undefined}
      style={{ "--ek": view.tone } as CSSProperties}
      onClick={toggle}
      onMouseEnter={() => window.clearTimeout(timer.current)}
      onMouseLeave={() => {
        if (!open) arm(LINGER_MS);
      }}
    >
      <span className={classes.mark}>
        {actor?.faction ? (
          <CircularFactionIcon faction={actor.faction} size={30} />
        ) : (
          <span className={classes.noFaction} />
        )}
        <span className={classes.glyph}>
          <Icon size={11} stroke={2.4} />
        </span>
      </span>
      <div className={classes.body}>
        <div className={classes.headline}>{view.headline}</div>
        {open && view.facts.length > 0 && (
          <div className={classes.facts}>
            {view.facts.map((fact) => (
              <span key={fact.key} className={classes.fact} data-tone={fact.tone}>
                {fact.text}
              </span>
            ))}
          </div>
        )}
        {open && hint && hint.lines.length > 0 && (
          <div className={classes.hint}>
            {hint.name && <b>{hint.name}</b>}
            {hint.meta && <small>{hint.meta}</small>}
            {hint.lines.map((line, index) => (
              <p key={index}>{line}</p>
            ))}
          </div>
        )}
      </div>
      {hasDetails && (
        <button
          type="button"
          className={classes.toggle}
          aria-expanded={open}
          aria-label={open ? "Hide details" : "Show details"}
          onClick={(e) => {
            e.stopPropagation();
            toggle();
          }}
        >
          <IconChevronDown size={14} />
        </button>
      )}
      <button
        type="button"
        className={classes.close}
        aria-label="Dismiss notification"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
      >
        <IconX size={14} />
      </button>
    </div>
  );
}

/**
 * Wyskakujące powiadomienia „kto co zrobił": każdy nowy wpis feedu Activity od INNEGO gracza
 * (użyta technologia, zagrana karta, ruch, walka…) pojawia się na chwilę w strefie komunikatów (``NotificationArea``) jako
 * JEDNA linia „kto co zrobił” i sam znika. Kliknięcie rozwija skutki i tekst karty/technologii
 * (to samo, co podpowiedź w panelu) i wstrzymuje zamknięcie. Pełna historia zostaje w panelu Activity.
 * Wpisy obecne przy otwarciu strony nie są nowością.
 */
export function ActivityToasts() {
  const { data } = useActivityFeed();
  const { data: me } = useNetworkMe();
  const ctx = useActivityContext(data?.players);
  const seen = useRef<number | null>(null);
  const [toasts, setToasts] = useState<ActivityEntry[]>([]);

  useEffect(() => {
    if (!data || me === undefined) return;
    const latest = data.entries.at(-1)?.seq ?? 0;
    if (seen.current === null || latest < seen.current) {
      // Pierwszy odczyt albo nowa gra: stare wpisy nie są nowością.
      seen.current = latest;
      return;
    }
    const since = seen.current;
    seen.current = Math.max(since, latest);
    const fresh = data.entries.filter(
      (e) =>
        e.seq > since &&
        (data.current_seq === null || e.seq <= data.current_seq) &&
        shouldToast(
          e,
          me.player_id,
          (id) => data.players[id]?.is_bot ?? false,
          me.network,
        ),
    );
    if (fresh.length === 0) return;
    setToasts((cur) => [...cur, ...fresh].slice(-MAX_VISIBLE));
  }, [data, me]);

  if (toasts.length === 0) return null;
  return (
    <div className={classes.stack} aria-live="polite" aria-label="Activity notifications">
      {toasts.map((entry) => (
        <ToastCard
          key={entry.seq}
          entry={entry}
          ctx={ctx}
          onClose={() => setToasts((cur) => cur.filter((t) => t.seq !== entry.seq))}
        />
      ))}
    </div>
  );
}
