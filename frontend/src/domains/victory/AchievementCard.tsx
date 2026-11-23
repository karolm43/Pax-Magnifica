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

/** Znaczek i kategoria na klucz osiągnięcia (klucze z `core/chronicle.py` i `gameStats.ts`). */
const META: Record<string, { icon: Icon; tag: AchievementTag }> = {
  greatest_battle: { icon: IconSwords, tag: "War" },
  longest_battle: { icon: IconHourglass, tag: "War" },
  crushing_victory: { icon: IconBolt, tag: "War" },
  unbreakable_wall: { icon: IconShield, tag: "War" },
  pyrrhic_victory: { icon: IconSkull, tag: "War" },
  mutual_destruction: { icon: IconFlame, tag: "War" },
  lord_of_the_void: { icon: IconRocket, tag: "War" },
  ground_master: { icon: IconTarget, tag: "War" },
  undefeated: { icon: IconMedal, tag: "War" },
  rivalry: { icon: IconInfinity, tag: "War" },
  warmonger: { icon: IconFlame, tag: "War" },
  besieged: { icon: IconShield, tag: "War" },
  conqueror: { icon: IconFlag, tag: "War" },
  torn_world: { icon: IconPlanet, tag: "War" },
  first_blood: { icon: IconDroplet, tag: "War" },
  blitzkrieg: { icon: IconTargetArrow, tag: "War" },
  capital_sacker: { icon: IconCrownOff, tag: "War" },
  home_sweet_home: { icon: IconHomeShield, tag: "War" },
  pacifist: { icon: IconPeace, tag: "Peace" },
  lead_changes: { icon: IconArrowsExchange, tag: "Race" },
  photo_finish: { icon: IconStopwatch, tag: "Race" },
  betrayal: { icon: IconSkull, tag: "Treachery" },
  quiet_victory: { icon: IconPeace, tag: "Peace" },
  peaceful_galaxy: { icon: IconPeace, tag: "Peace" },
  diplomat: { icon: IconHeartHandshake, tag: "Table" },
  hermit: { icon: IconMoodSad, tag: "Table" },
  benefactor: { icon: IconGift, tag: "Table" },
  comeback: { icon: IconTrendingUp, tag: "Race" },
  fallen_favorite: { icon: IconTrendingDown, tag: "Race" },
  round_to_remember: { icon: IconStar, tag: "Race" },
  wire_to_wire: { icon: IconCrown, tag: "Race" },
  throne_room: { icon: IconBuildingCastle, tag: "Empire" },
  legend_collector: { icon: IconDiamond, tag: "Empire" },
  homeworld_hunter: { icon: IconHome, tag: "Empire" },
  exile: { icon: IconHomeOff, tag: "Empire" },
  master_builder: { icon: IconBuilding, tag: "Empire" },
  everywhere: { icon: IconCompass, tag: "Empire" },
  // Nagrody statystyczne (gameStats.ts)
  planets: { icon: IconWorld, tag: "Empire" },
  fleet: { icon: IconRocket, tag: "War" },
  ground: { icon: IconTarget, tag: "War" },
  techs: { icon: IconBolt, tag: "Empire" },
  tg: { icon: IconCoins, tag: "Empire" },
  economy: { icon: IconCoins, tag: "Empire" },
  relics: { icon: IconDiamond, tag: "Empire" },
  secrets: { icon: IconUsers, tag: "Race" },
  runner_up: { icon: IconTrophy, tag: "Race" },
  wooden_spoon: { icon: IconMoodSad, tag: "Race" },
};

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