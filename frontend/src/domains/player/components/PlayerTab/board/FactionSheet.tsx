import { useEffect, useMemo, useState } from "react";
import { portraitCandidates } from "@/domains/setup/FactionBackdrop";
import { Ability } from "@/domains/player/components/Ability";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { getAbility } from "@/entities/lookup/abilities";
import { lookupUnit } from "@/entities/lookup/units";
import { attribution, quoted } from "@/entities/lore/typography";
import type { PlayerData } from "@/entities/data/types";
import { factionQuote, LoreButton } from "./LoreButton";
import { SheetUnit } from "./SheetUnit";
import styles from "./FactionSheet.module.css";

/*
 * Center of the player zone: the faction sheet. Name and emblem over the portrait on a
 * starfield, the flagship top-left, abilities and commodities on the right, and the unit grid
 * in the printed order.
 */

/** Printed grid order; `area` is the CSS grid area of the unit. */
const GRID_UNITS = [
  { asyncId: "ws", area: "ws" },
  { asyncId: "ca", area: "ca" },
  { asyncId: "dn", area: "dn" },
  { asyncId: "dd", area: "dd" },
  { asyncId: "pd", area: "pd" },
  { asyncId: "cv", area: "cv" },
  { asyncId: "ff", area: "ff" },
  { asyncId: "gf", area: "gf" },
  { asyncId: "sd", area: "sd" },
];

/** First portrait source that loads; the icon fallback is skipped (the emblem is already there). */
function Portrait({ player }: { player: PlayerData }) {
  const candidates = useMemo(
    () => portraitCandidates({ id: player.faction, leaders: player.leaderIDs ?? [] }).slice(0, -1),
    [player.faction, player.leaderIDs],
  );
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [candidates]);
  if (index >= candidates.length) return null;
  return (
    <img
      key={candidates[index]}
      src={candidates[index]}
      alt=""
      className={styles.portrait}
      onError={() => setIndex((i) => i + 1)}
    />
  );
}

function Abilities({ ids }: { ids: string[] }) {
  return (
    <section className={styles.abilities} aria-label="Faction abilities">
      {ids.map((id) => {
        const data = getAbility(id);
        if (!data) return null;
        return (
          <div key={id} className={styles.abilityEntry}>
            <Ability id={id} />
            {data.permanentEffect && <p>{data.permanentEffect}</p>}
            {(data.window || data.windowEffect) && (
              <p>
                {data.window && <em className={styles.abilityWindow}>{data.window}</em>}
                {data.windowEffect}
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}

function Commodities({ value, max }: { value: number; max: number }) {
  return (
    <section className={styles.commodities} aria-label="Commodities">
      <img src="/comms.png" alt="" />
      <b className={styles.commodityMax}>{max}</b>
      <span className={styles.commodityLabel}>
        Commodities
        <strong aria-label={`${value} of ${max} commodities`}>
          {value} / {max}
        </strong>
      </span>
    </section>
  );
}

export function FactionSheet({ player }: { player: PlayerData }) {
  const fields = getPlayerCardLayoutFields(player);
  const name = fields.factionDisplayName;
  const { quote, author } = factionQuote(player.faction);
  const monument = lookupUnit("monument", player.faction, player);

  return (
    <section className={styles.sheetFrame} aria-label={`${name} faction sheet`}>
      <div className={styles.sheet}>
        <div className={styles.backdrop} aria-hidden="true">
          <Portrait key={player.faction} player={player} />
        </div>

        <h2 className={styles.title}>{name}</h2>

        <div className={styles.lore}>
          {player.faction ? <CircularFactionIcon faction={player.faction} size={76} /> : null}
          {quote && (
            <figure className={styles.quote}>
              <blockquote>{quoted(quote)}</blockquote>
              {author && <figcaption>{attribution(author)}</figcaption>}
            </figure>
          )}
          <LoreButton faction={player.faction} factionName={name} />
        </div>

        <SheetUnit
          asyncId="fs"
          player={player}
          variant="flagship"
          subtitle={`${name} flagship`}
          className={styles.fs}
        />

        <div className={styles.abil}>
          <Abilities ids={player.abilities ?? []} />
        </div>
        <div className={styles.comm}>
          <Commodities value={player.commodities ?? 0} max={player.commoditiesTotal ?? 0} />
        </div>

        {GRID_UNITS.map(({ asyncId, area }) => (
          <SheetUnit key={asyncId} asyncId={asyncId} player={player} className={styles[area]} />
        ))}
        {monument && <SheetUnit asyncId="monument" player={player} />}
      </div>
    </section>
  );
}
