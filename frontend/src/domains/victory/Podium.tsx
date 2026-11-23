// Podium ekranu końcowego: trzy pierwsze miejsca (2 · 1 · 3) z portretami frakcji.
// Portret stoi ostro w środku kolumny, a jego boki (lewy i prawy) przechodzą w rozmytą
// kopię tego samego obrazu — tak samo dla pliku z przezroczystością i dla prostokątnego
// portretu bohatera. Kliknięcie miejsca filtruje osiągnięcia do tego gracza.

import { useMemo, useState, type CSSProperties } from "react";
import { IconCrown } from "@tabler/icons-react";
import type { FactionInfo } from "@/api/useNewGame";
import { portraitCandidates } from "@/domains/setup/FactionBackdrop";
import type { PlayerSummary } from "./gameStats";
import styles from "./Podium.module.css";

export interface PodiumPlace {
  row: PlayerSummary;
  factionName: string;
  playerName: string;
  swatch?: string;
  /** Liczba osiągnięć gracza (kronika + wyróżnienia). */
  honors: number;
}

const PLACE_LABEL = ["1st", "2nd", "3rd"];
/** Kolejność kolumn na ekranie: drugie miejsce po lewej, pierwsze w środku, trzecie po prawej. */
const SCREEN_ORDER = [1, 0, 2];

function Portrait({ factionId, faction }: { factionId: string; faction?: FactionInfo }) {
  const candidates = useMemo(
    () =>
      portraitCandidates(
        faction ?? ({ id: factionId, leaders: [] } as unknown as FactionInfo),
      ),
    [faction, factionId],
  );
  const [index, setIndex] = useState(0);
  if (index >= candidates.length) return null;
  const src = candidates[index];
  const isIcon = index === candidates.length - 1;
  return (
    <div className={styles.portrait} data-icon={isIcon || undefined}>
      <img src={src} alt="" className={styles.blur} aria-hidden />
      <img
        src={src}
        alt=""
        className={styles.figure}
        onError={() => setIndex((i) => i + 1)}
      />
    </div>
  );
}

export function Podium({
  places,
  factionById,
  selected,
  onSelect,
}: {
  places: PodiumPlace[];
  factionById: Map<string, FactionInfo>;
  /** Gracz, do którego zawężono osiągnięcia (null = wszyscy). */
  selected: string | null;
  onSelect: (playerId: string | null) => void;
}) {
  const top = places.slice(0, 3);
  if (top.length === 0) return null;
  return (
    <ol className={styles.podium} aria-label="Podium">
      {SCREEN_ORDER.filter((i) => i < top.length).map((i) => {
        const place = top[i];
        const id = place.row.player.discordId;
        const active = selected === id;
        return (
          <li
            key={id}
            className={styles.place}
            data-place={i + 1}
            data-dim={(selected !== null && !active) || undefined}
            style={
              {
                ...(place.swatch ? { "--player": place.swatch } : {}),
                "--delay": `${(2 - i) * 0.35}s`,
              } as CSSProperties
            }
          >
            <button
              type="button"
              className={styles.hit}
              aria-pressed={active}
              aria-label={`${PLACE_LABEL[i]} place: ${place.factionName}. Show their achievements`}
              onClick={() => onSelect(active ? null : id)}
            >
              <Portrait
                factionId={place.row.player.faction}
                faction={factionById.get(place.row.player.faction)}
              />
              <div className={styles.plinth}>
                <span className={styles.rank} aria-hidden>
                  {i === 0 ? <IconCrown size={26} stroke={1.6} /> : null}
                  {i + 1}
                </span>
                <span className={styles.name}>
                  <img
                    src={`/static/factions/${place.row.player.faction}.png`}
                    alt=""
                    width={26}
                    height={26}
                    className={styles.crest}
                    onError={(e) => {
                      e.currentTarget.style.visibility = "hidden";
                    }}
                  />
                  {place.factionName}
                </span>
                <span className={styles.player}>
                  <span className={styles.dot} aria-hidden />
                  {place.playerName}
                </span>
                <span className={styles.numbers}>
                  <b>{place.row.vp}</b> VP
                  {place.honors > 0 && (
                    <span className={styles.honors}>
                      {place.honors} honor{place.honors === 1 ? "" : "s"}
                    </span>
                  )}
                </span>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
