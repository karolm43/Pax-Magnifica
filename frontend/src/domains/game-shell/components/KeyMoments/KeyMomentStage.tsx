import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { IconPlayerTrackNext } from "@tabler/icons-react";
import { useActivityFeed, type ActivityPlayer } from "@/api/useBoardEditor";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { useDiceStage } from "@/domains/dice/diceStage";
import { useSettingsStore } from "@/state/appStore";
import { lookupCardLore } from "@/entities/lore/lookupLore";
import { getLeaderById } from "@/entities/lookup/leaders";
import { breakthroughs } from "@/entities/data/breakthroughs";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { seatColorStyle } from "@/domains/game-shell/components/FactionsInGame/seatColor";
import { useFactions, type FactionInfo } from "@/api/useNewGame";
import { FactionPortraitLayer } from "@/domains/setup/FactionBackdrop";
import { momentsForEntry, type KeyMoment } from "./keyMoments";
import { HERO_BOARD_FX, coversForQueue, useHeroFx } from "./heroBoardFx";
import styles from "./KeyMomentStage.module.css";

/** Czas sceny (ms) bez wygaszania. */
const DURATION: Record<KeyMoment["kind"], number> = {
  hero: 5600,
  fracture: 5200,
  breakthrough: 4000,
  custodians: 4200,
};
/** Wygaszanie sceny (zgodne z CSS `.leaving`). */
const LEAVE_MS = 450;
/** Rzut d10 (np. na wejście Fracture) najpierw ląduje i chwilę widać wynik. */
const DICE_READ_MS = 1400;
/** Rzut z `gameState.tableRoll` startuje chwilę po wpisie feedu — dajemy mu czas pojawić się. */
const DICE_GRACE_MS = 600;
/** Nie czekamy na kości dłużej niż tyle. */
const DICE_MAX_WAIT_MS = 7000;

const isHero = (id: string) => getLeaderById(id)?.type === "hero";

function diceBusyUntil(): number {
  const roll = useDiceStage.getState().roll;
  return roll ? roll.id + roll.diceMs + DICE_READ_MS : 0;
}

function nameOf(p: ActivityPlayer | undefined, id: string | null): string {
  if (!id) return "";
  return p?.display_name.trim() || p?.faction || id;
}

/** Podpis „kto” — ikona frakcji + nazwa gracza (ten sam chip frakcji co w feedzie). */
function Who({ player, id, prefix }: { player: ActivityPlayer | undefined; id: string | null; prefix?: string }) {
  if (!id) return null;
  return (
    <span className={styles.who}>
      {player?.faction && <CircularFactionIcon faction={player.faction} size={26} />}
      <span>
        {prefix && <small>{prefix} </small>}
        {nameOf(player, id)}
      </span>
    </span>
  );
}

function HeroScene({ moment, player }: { moment: Extract<KeyMoment, { kind: "hero" }>; player: ActivityPlayer | undefined }) {
  const leader = getLeaderById(moment.leaderId);
  const { data: factions } = useFactions();
  // Portret frakcji ze sceny wyboru frakcji (ten sam komponent i kadr co ekran zwycięstwa):
  // postać przy lewej i dolnej krawędzi, tekst zaczyna się przy prawej krawędzi sylwetki.
  const factionId = player?.faction ?? leader?.faction ?? "";
  const faction =
    factions?.find((f) => f.id === factionId) ??
    ({ id: factionId, leaders: [moment.leaderId] } as unknown as FactionInfo);
  const [figureCx, setFigureCx] = useState<number | null>(null);
  return (
    <>
      <div className={styles.heroGlow} />
      <div
        className={styles.heroPortraitZone}
        style={figureCx !== null ? ({ "--figure-cx": `${figureCx}px` } as CSSProperties) : undefined}
      >
        {factionId && <FactionPortraitLayer faction={faction} onFigureCenter={setFigureCx} softEdge />}
      </div>
      <div
        className={styles.heroCopy}
        style={figureCx !== null ? ({ "--figure-cx": `${figureCx}px` } as CSSProperties) : undefined}
      >
        <span className={styles.eyebrow}>Hero unleashed</span>
        <h2 className={styles.heroName}>{leader?.name ?? moment.leaderId}</h2>
        {leader?.title && <span className={styles.heroTitle}>{leader.title}</span>}
        <span className={styles.rule} />
        {leader?.abilityName && <span className={styles.ability}>{leader.abilityName}</span>}
        {leader?.abilityText && (
          <p className={styles.abilityText}>
            {leader.abilityWindow ? <b>{leader.abilityWindow.replace(/:\s*$/, "")}: </b> : null}
            {leader.abilityText}
          </p>
        )}
        {lookupCardLore("leader", moment.leaderId) && (
          <p className={styles.heroLore}>{lookupCardLore("leader", moment.leaderId)}</p>
        )}
        <Who player={player} id={moment.player} />
      </div>
    </>
  );
}

/** Szczelina przez cały ekran (łamana) — rysowana kreską, z poświatą. */
const RIFT_PATH =
  "M -20 340 L 140 318 L 230 372 L 360 300 L 470 352 L 560 262 L 650 330 L 760 286 L 850 352 L 980 296 L 1080 344 L 1220 300";

function FractureScene({ moment, player }: { moment: Extract<KeyMoment, { kind: "fracture" }>; player: ActivityPlayer | undefined }) {
  return (
    <>
      <div className={styles.riftFlash} />
      <svg className={styles.rift} viewBox="0 0 1200 640" preserveAspectRatio="none" aria-hidden="true">
        <path className={styles.riftGlow} d={RIFT_PATH} />
        <path className={styles.riftCore} d={RIFT_PATH} />
      </svg>
      <div className={styles.shards}>
        {Array.from({ length: 14 }, (_, i) => (
          <i key={i} style={{ "--i": i } as CSSProperties} />
        ))}
      </div>
      <div className={styles.centerCopy}>
        <span className={styles.eyebrow}>Thunder&apos;s Edge</span>
        <h2 className={styles.fractureTitle} data-text="The Fracture">
          The Fracture
        </h2>
        <span className={styles.subline}>has entered play</span>
        <Who player={player} id={moment.player} prefix="Opened by" />
      </div>
    </>
  );
}

function BreakthroughScene({ moment, player }: { moment: Extract<KeyMoment, { kind: "breakthrough" }>; player: ActivityPlayer | undefined }) {
  const bt = breakthroughs.find((b) => b.faction === player?.faction);
  return (
    <>
      <div className={styles.rings}>
        <i />
        <i />
        <i />
      </div>
      <div className={styles.centerCopy}>
        <span className={styles.eyebrow}>Breakthrough</span>
        <h2 className={styles.centerTitle}>{bt?.displayName ?? bt?.name ?? "Breakthrough"}</h2>
        {bt?.text && <p className={styles.abilityText} data-center>{bt.text}</p>}
        <Who player={player} id={moment.player} />
      </div>
    </>
  );
}

function CustodiansScene({ moment, player }: { moment: Extract<KeyMoment, { kind: "custodians" }>; player: ActivityPlayer | undefined }) {
  return (
    <>
      <div className={styles.rings} data-gold>
        <i />
        <i />
      </div>
      <div className={styles.centerCopy}>
        <img className={styles.token} src={assetUrl("/tokens/token_custodianvp.png")} alt="" />
        <span className={styles.eyebrow}>Mecatol Rex</span>
        <h2 className={styles.centerTitle}>The Custodians stand down</h2>
        <span className={styles.subline}>Custodians token removed · +1 victory point</span>
        <Who player={player} id={moment.player} />
      </div>
    </>
  );
}

/**
 * Kluczowe momenty gry (RULES.md 64): użycie bohatera, wejście The Fracture, zdobyty przełom,
 * zdjęcie żetonu Custodians. Każdy NOWY wpis feedu Activity z takim faktem odtwarza krótką
 * scenę u WSZYSTKICH graczy (także u sprawcy). Sceny idą w kolejce; „Skip” / Esc ją pomija.
 * Warstwa nie blokuje planszy (`pointer-events: none` poza przyciskiem). `adminFastMode` wyłącza.
 */
export function KeyMomentStage() {
  const { data: feed } = useActivityFeed();
  const { data: me } = useNetworkMe();
  const adminFastMode = useSettingsStore((s) => s.settings.adminFastMode);
  const seen = useRef<number | null>(null);
  const [queue, setQueue] = useState<KeyMoment[]>([]);
  // wait -> on (scena) -> leaving (wygaszanie) -> [board: efekt bohatera na mapie] -> następny.
  const [shown, setShown] = useState<"wait" | "on" | "leaving" | "board">("wait");
  const playFx = useHeroFx((s) => s.play);
  const stopFx = useHeroFx((s) => s.stop);

  useEffect(() => {
    if (!feed || me === undefined) return;
    const latest = feed.entries.at(-1)?.seq ?? 0;
    if (seen.current === null || latest < seen.current) {
      seen.current = latest; // pierwszy odczyt / nowa gra — stare wpisy nie są nowością
      return;
    }
    const since = seen.current;
    seen.current = Math.max(since, latest);
    if (adminFastMode) return;
    const fresh = feed.entries
      .filter((e) => e.seq > since && (feed.current_seq === null || e.seq <= feed.current_seq))
      .flatMap((e) => momentsForEntry(e, isHero));
    if (fresh.length > 0) setQueue((cur) => [...cur, ...fresh]);
  }, [feed, me, adminFastMode]);

  const current = queue[0];

  // Wymieniony kafel (Nova Seed) czeka pod starym obrazem, aż efekt na planszy go odsłoni.
  const setCovers = useHeroFx((s) => s.setCovers);
  useEffect(() => {
    setCovers(coversForQueue(queue));
  }, [queue, setCovers]);
  useEffect(() => () => setCovers({}), [setCovers]);
  // Scena reliktu (RelicRevealWatcher) czeka, aż kolejka momentów się opróżni.
  const setStageBusy = useHeroFx((s) => s.setStageBusy);
  useEffect(() => {
    setStageBusy(queue.length > 0);
  }, [queue, setStageBusy]);
  useEffect(() => () => setStageBusy(false), [setStageBusy]);

  // Start sceny: najpierw niech wyląduje kość (rzut d10 na Fracture), potem scena.
  useEffect(() => {
    if (!current) return;
    setShown("wait");
    const began = Date.now();
    let timer = 0;
    const tryStart = () => {
      const waited = Date.now() - began;
      const busy = diceBusyUntil() - Date.now();
      if (waited < DICE_GRACE_MS && current.kind === "fracture") {
        timer = window.setTimeout(tryStart, DICE_GRACE_MS - waited);
      } else if (busy > 0 && waited < DICE_MAX_WAIT_MS) {
        timer = window.setTimeout(tryStart, Math.min(busy, 400));
      } else {
        setShown("on");
      }
    };
    tryStart();
    return () => window.clearTimeout(timer);
  }, [current]);

  // Przepis efektu na planszy (tylko bohaterowie z wpisem w HERO_BOARD_FX).
  const recipe = current?.kind === "hero" ? HERO_BOARD_FX[current.leaderId] : undefined;
  const owner = current?.player ? feed?.players[current.player] : undefined;

  useEffect(() => {
    if (!current || shown === "wait") return;
    const next = () => setQueue((cur) => cur.slice(1));
    let timer: number;
    if (shown === "on") timer = window.setTimeout(() => setShown("leaving"), DURATION[current.kind]);
    else if (shown === "leaving")
      timer = window.setTimeout(() => (recipe ? setShown("board") : next()), LEAVE_MS);
    else timer = window.setTimeout(next, recipe?.ms ?? 0);
    return () => window.clearTimeout(timer);
  }, [current, shown, recipe]);

  // Efekt na mapie trwa tylko w stanie „board”; zdjęcie (koniec / Skip / nowa gra) czyści warstwę.
  useEffect(() => {
    if (shown !== "board" || current?.kind !== "hero" || !recipe) return;
    playFx({
      heroId: current.leaderId,
      recipe,
      faction: owner?.faction ?? null,
      color: owner?.color ?? null,
      replaced: current.replaced,
      planets: current.planets,
      areas: current.areas,
    });
    return () => stopFx();
    // Zależności celowo tylko [shown, current]: jeden start na wejście w „board”.
  }, [shown, current]);

  // Skip / Esc: ze sceny przechodzi do efektu na planszy (albo dalej), z planszy kończy moment.
  const skip = () => {
    if (shown === "board") setQueue((cur) => cur.slice(1));
    else setShown("leaving");
  };
  const skipRef = useRef(skip);
  skipRef.current = skip;
  useEffect(() => {
    if (!current || (shown !== "on" && shown !== "board")) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") skipRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, shown]);

  if (!current || shown === "wait") return null;
  const player = owner;
  if (shown === "board") {
    // Sama plansza gra efekt — zostaje tylko dyskretny „Skip”.
    return (
      <button type="button" className={styles.skip} data-board onClick={skip}>
        Skip <IconPlayerTrackNext size={14} />
      </button>
    );
  }
  let scene: ReactNode;
  switch (current.kind) {
    case "hero":
      scene = <HeroScene moment={current} player={player} />;
      break;
    case "fracture":
      scene = <FractureScene moment={current} player={player} />;
      break;
    case "breakthrough":
      scene = <BreakthroughScene moment={current} player={player} />;
      break;
    case "custodians":
      scene = <CustodiansScene moment={current} player={player} />;
      break;
  }
  return (
    <div
      key={`${current.seq}-${current.kind}`}
      className={styles.stage}
      data-kind={current.kind}
      data-leaving={shown === "leaving" || undefined}
      style={player?.color ? seatColorStyle(player.color) : undefined}
      role="status"
      aria-live="polite"
    >
      <div className={styles.letterbox} data-top />
      <div className={styles.letterbox} />
      <div className={styles.scene}>{scene}</div>
      <button type="button" className={styles.skip} onClick={skip}>
        Skip <IconPlayerTrackNext size={14} />
      </button>
    </div>
  );
}
