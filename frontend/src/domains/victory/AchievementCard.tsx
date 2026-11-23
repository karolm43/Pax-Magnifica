// Jedna, ujednolicona karta osiągnięcia dla podsumowania końcowego (kronika wojny i nagrody).
// Wszystkie karty mają ten sam rozmiar i układ: znaczek + kategoria + duża liczba (stat),
// tytuł, opis oraz stopka z uczestnikami (herb frakcji, nazwa, gracz). Kolor zależy od
// kategorii, nie od gracza, więc rząd kart czyta się jak legenda.

import { useMemo, useState, type CSSProperties } from "react";
import {
  IconAward,
  IconBolt,
  IconBuilding,
  IconBuildingCastle,
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
  IconArrowBackUp,
  IconBandage,
  IconBomb,
  IconBuildingBank,
  IconCards,
  IconChessKing,
  IconClockPause,
  IconFeather,
  IconHeartBroken,
  IconLockOpen,
  IconLuggage,
  IconMeteor,
  IconPlant,
  IconRoute,
  IconShieldHalf,
  IconSpeakerphone,
  IconSun,
  IconSword,
  IconTelescope,
  IconThumbDown,
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
  ArrowBackUp: IconArrowBackUp,
  Bandage: IconBandage,
  Bomb: IconBomb,
  BuildingBank: IconBuildingBank,
  Cards: IconCards,
  ChessKing: IconChessKing,
  ClockPause: IconClockPause,
  Feather: IconFeather,
  HeartBroken: IconHeartBroken,
  LockOpen: IconLockOpen,
  Luggage: IconLuggage,
  Meteor: IconMeteor,
  Plant: IconPlant,
  Route: IconRoute,
  ShieldHalf: IconShieldHalf,
  Speakerphone: IconSpeakerphone,
  Sun: IconSun,
  Sword: IconSword,
  Telescope: IconTelescope,
  ThumbDown: IconThumbDown,
  World: IconWorld,
};

const META: Record<string, { icon: Icon; tag: AchievementTag }> = Object.fromEntries(
  Object.entries(catalog.achievements).map(([key, entry]) => [
    key,
    { icon: ICONS[entry.icon] ?? IconAward, tag: entry.tag as AchievementTag },
  ]),
);

const FALLBACK = { icon: IconAward, tag: "Table" as AchievementTag };

export function achievementTag(key: string): AchievementTag {
  return (META[key] ?? FALLBACK).tag;
}

export function AchievementCard({ item, index = 0 }: { item: AchievementData; index?: number }) {
  const meta = META[item.key] ?? FALLBACK;
  const Glyph = meta.icon;
  return (
    <li
      className={styles.card}
      data-tag={meta.tag}
      data-key={item.key}
      style={{ "--i": index } as CSSProperties}
    >
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



/** Kolejność kategorii w filtrze i w siatce. */
const TAG_ORDER: AchievementTag[] = ["War", "Treachery", "Table", "Race", "Empire", "Peace"];

/**
 * Tablica osiągnięć: chipy kategorii (z liczbą) nad responsywną siatką kart — wszystko
 * widoczne naraz, bez przewijania w bok. ``playerId`` zawęża karty do jednego gracza
 * (wybór na podium).
 */
export function AchievementBoard({
  title,
  items,
  players,
  playerId,
  onSelectPlayer,
}: {
  title: string;
  items: AchievementData[];
  /** Wszyscy gracze partii — każdy może podejrzeć swoje osiągnięcia. */
  players: AchievementPlayer[];
  playerId: string | null;
  onSelectPlayer: (playerId: string | null) => void;
}) {
  const [tag, setTag] = useState<AchievementTag | null>(null);
  const forPlayer = useMemo(
    () =>
      playerId === null
        ? items
        : items.filter((item) => item.players.some((p) => p.id === playerId)),
    [items, playerId],
  );
  const sorted = useMemo(
    () =>
      [...forPlayer].sort(
        (a, b) =>
          TAG_ORDER.indexOf(achievementTag(a.key)) - TAG_ORDER.indexOf(achievementTag(b.key)),
      ),
    [forPlayer],
  );
  const counts = useMemo(() => {
    const out = new Map<AchievementTag, number>();
    for (const item of forPlayer) {
      const t = achievementTag(item.key);
      out.set(t, (out.get(t) ?? 0) + 1);
    }
    return out;
  }, [forPlayer]);
  const shown = tag === null ? sorted : sorted.filter((item) => achievementTag(item.key) === tag);

  if (items.length === 0) return null;
  return (
    <section className={styles.board} aria-label={title}>
      <h2 className={styles.boardTitle}>
        {title}
        <span className={styles.count}>{forPlayer.length}</span>
      </h2>
      <div className={styles.filters} role="group" aria-label="Filter by player">
        <button
          type="button"
          className={styles.filter}
          aria-pressed={playerId === null}
          onClick={() => onSelectPlayer(null)}
        >
          All players
        </button>
        {players.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`${styles.filter} ${styles.filterPlayer}`}
            style={p.swatch ? ({ "--player": p.swatch } as CSSProperties) : undefined}
            aria-pressed={playerId === p.id}
            onClick={() => onSelectPlayer(playerId === p.id ? null : p.id)}
          >
            <img
              src={`/static/factions/${p.faction}.png`}
              alt=""
              width={20}
              height={20}
              className={styles.crest}
              onError={(e) => {
                e.currentTarget.style.visibility = "hidden";
              }}
            />
            {p.factionName}
            <b>{items.filter((item) => item.players.some((q) => q.id === p.id)).length}</b>
          </button>
        ))}
      </div>
      <div className={styles.filters} role="group" aria-label="Filter by category">
        <button
          type="button"
          className={styles.filter}
          aria-pressed={tag === null}
          onClick={() => setTag(null)}
        >
          All <b>{forPlayer.length}</b>
        </button>
        {TAG_ORDER.filter((t) => counts.has(t)).map((t) => (
          <button
            key={t}
            type="button"
            className={styles.filter}
            data-tag={t}
            aria-pressed={tag === t}
            onClick={() => setTag(tag === t ? null : t)}
          >
            {t} <b>{counts.get(t)}</b>
          </button>
        ))}
      </div>
      {shown.length > 0 ? (
        <ul className={styles.grid} key={`${tag ?? "all"}:${playerId ?? "all"}`}>
          {shown.map((item, i) => (
            <AchievementCard key={item.key} item={item} index={i} />
          ))}
        </ul>
      ) : (
        <p className={styles.empty}>No achievements here.</p>
      )}
    </section>
  );
}
