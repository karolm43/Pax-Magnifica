// Jedna, ujednolicona karta osiągnięcia dla podsumowania końcowego (kronika wojny i nagrody).
// Wszystkie karty mają ten sam rozmiar i układ: znaczek + kategoria + duża liczba (stat),
// tytuł, opis oraz stopka z uczestnikami (herb frakcji, nazwa, gracz). Kolor zależy od
// kategorii, nie od gracza, więc rząd kart czyta się jak legenda.

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import {
  IconAward,
  IconBolt,
  IconBuilding,
  IconBuildingCastle,
  IconChevronLeft,
  IconChevronRight,
  IconCoins,
  IconTargetArrow,
  IconStopwatch,
  IconHomeShield,
  IconDroplet,
  IconCrownOff,
  IconArrowsExchange,
  IconCompass,
  IconCrown,
  IconDiamond,
  IconFlag,
  IconFlame,
  IconGift,
  IconHeartHandshake,
  IconHome,
  IconHomeOff,
  IconHourglass,
  IconInfinity,
  IconMedal,
  IconMoodSad,
  IconPeace,
  IconPlanet,
  IconRocket,
  IconShield,
  IconSkull,
  IconStar,
  IconSwords,
  IconTarget,
  IconTrendingDown,
  IconTrendingUp,
  IconTrophy,
  IconUsers,
  IconWorld,
} from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";
import styles from "./AchievementCard.module.css";
import catalog from "../../../../assets/config/achievements.json";

export type AchievementTag = "War" | "Treachery" | "Peace" | "Race" | "Empire" | "Table";

export interface AchievementPlayer {
  id: string;
  faction: string;
  factionName: string;
  playerName: string;
  /** Kolor gracza (CSS) do kropki przy nazwie. */
  swatch?: string;
}

export interface AchievementData {
  key: string;
  title: string;
  detail: string;
  /** Krótka, duża liczba/hasło po prawej w nagłówku (np. „12 units lost"). */
  stat: string;
  players: AchievementPlayer[];
}

/**
 * Znaczek i kategoria na klucz osiągnięcia — z `assets/config/achievements.json` (jedno miejsce
 * edycji). Nazwa ikony z JSON musi być w `ICONS`; pilnuje tego `achievements.test.ts`.
 */
export const ICONS: Record<string, Icon> = {
  ArrowsExchange: IconArrowsExchange,
  Bolt: IconBolt,
  Building: IconBuilding,
  BuildingCastle: IconBuildingCastle,
  Coins: IconCoins,
  Compass: IconCompass,
  Crown: IconCrown,
  CrownOff: IconCrownOff,
  Diamond: IconDiamond,
  Droplet: IconDroplet,
  Flag: IconFlag,
  Flame: IconFlame,
  Gift: IconGift,
  HeartHandshake: IconHeartHandshake,
  Home: IconHome,
  HomeOff: IconHomeOff,
  HomeShield: IconHomeShield,
  Hourglass: IconHourglass,
  Infinity: IconInfinity,
  Medal: IconMedal,
  MoodSad: IconMoodSad,
  Peace: IconPeace,
  Planet: IconPlanet,
  Rocket: IconRocket,
  Shield: IconShield,
  Skull: IconSkull,
  Star: IconStar,
  Stopwatch: IconStopwatch,
  Swords: IconSwords,
  Target: IconTarget,
  TargetArrow: IconTargetArrow,
  TrendingDown: IconTrendingDown,
  TrendingUp: IconTrendingUp,
  Trophy: IconTrophy,
  Users: IconUsers,
  World: IconWorld,
};

const META: Record<string, { icon: Icon; tag: AchievementTag }> = Object.fromEntries(
  Object.entries(catalog.achievements).map(([key, entry]) => [
    key,
    { icon: ICONS[entry.icon] ?? IconAward, tag: entry.tag as AchievementTag },
  ]),
);

const FALLBACK = { icon: IconAward, tag: "Table" as AchievementTag };

export function AchievementCard({ item }: { item: AchievementData }) {
  const meta = META[item.key] ?? FALLBACK;
  const Glyph = meta.icon;
  return (
    <li className={styles.card} data-tag={meta.tag} data-key={item.key}>
      <header className={styles.head}>
        <span className={styles.badge} aria-hidden>
          <Glyph size={22} stroke={1.8} />
        </span>
        <span className={styles.tag}>{meta.tag}</span>
        {item.stat && <b className={styles.stat}>{item.stat}</b>}
      </header>
      <h3 className={styles.title}>{item.title}</h3>
      <p className={styles.detail}>{item.detail}</p>
      <footer className={styles.who}>
        {item.players.map((p) => (
          <span
            key={p.id}
            className={styles.player}
            style={p.swatch ? ({ "--player": p.swatch } as CSSProperties) : undefined}
          >
            <img
              src={`/static/factions/${p.faction}.png`}
              alt=""
              width={26}
              height={26}
              className={styles.crest}
              onError={(e) => {
                e.currentTarget.style.visibility = "hidden";
              }}
            />
            <span className={styles.playerName}>
              {p.factionName}
              <small>{p.playerName}</small>
            </span>
          </span>
        ))}
      </footer>
    </li>
  );
}


/**
 * Sekcja z poziomo przewijanym rzędem kart (swipe/kółko/strzałki). Karty mają stałą
 * szerokość i zatrzymują się na początku karty (scroll-snap); strzałki pokazują się tylko,
 * gdy jest dokąd przewijać.
 */
export function AchievementRow({
  title,
  items,
}: {
  title: string;
  items: AchievementData[];
}) {
  const listRef = useRef<HTMLUListElement>(null);
  const [edge, setEdge] = useState({ left: false, right: false });

  const update = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    setEdge({
      left: el.scrollLeft > 4,
      right: el.scrollLeft + el.clientWidth < el.scrollWidth - 4,
    });
  }, []);

  useEffect(() => {
    update();
    const el = listRef.current;
    if (!el) return;
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [update, items.length]);

  const page = (direction: -1 | 1) => {
    const el = listRef.current;
    if (el) el.scrollBy({ left: direction * el.clientWidth * 0.85, behavior: "smooth" });
  };

  if (items.length === 0) return null;
  return (
    <section className={styles.row} aria-label={title}>
      <h2 className={styles.rowTitle}>
        {title}
        <span className={styles.count}>{items.length}</span>
      </h2>
      <div className={styles.scroller}>
        {edge.left && (
          <button
            type="button"
            className={`${styles.arrow} ${styles.arrowLeft}`}
            onClick={() => page(-1)}
            aria-label={`${title}: previous`}
          >
            <IconChevronLeft size={22} />
          </button>
        )}
        <ul ref={listRef} className={styles.track} onScroll={update}>
          {items.map((item) => (
            <AchievementCard key={item.key} item={item} />
          ))}
        </ul>
        {edge.right && (
          <button
            type="button"
            className={`${styles.arrow} ${styles.arrowRight}`}
            onClick={() => page(1)}
            aria-label={`${title}: next`}
          >
            <IconChevronRight size={22} />
          </button>
        )}
      </div>
    </section>
  );
}