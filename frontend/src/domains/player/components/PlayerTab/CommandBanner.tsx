import { useEffect, useMemo, useState } from "react";
import { IconBook2, IconFlag } from "@tabler/icons-react";
import { Button } from "@/ds";
import { portraitCandidates } from "@/domains/setup/FactionBackdrop";
import { HeaderTokens } from "@/domains/player/components/PlayerCardHeader/PlayerCardHeaderCompact";
import { getPlayerCardLayoutFields } from "@/domains/player/components/PlayerCardShared/getPlayerCardLayoutFields";
import { NeedsToFollow } from "@/domains/player/components/NeedsToFollow";
import { Neighbors } from "@/domains/player/components/Neighbors";
import { Breakthrough } from "@/domains/player/components/Breakthrough/Breakthrough";
import breakthroughStyles from "@/domains/player/components/Breakthrough/Breakthrough.module.css";
import { playerName } from "@/domains/strategy/PlayerChip";
import { getFactionLore, loreToBlocks } from "@/entities/lore/factionLore";
import { attribution, quoted } from "@/entities/lore/typography";
import type { PlayerData } from "@/entities/data/types";
import { AppModal } from "@/shared/ui/AppModal";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { useSettingsStore } from "@/state/appStore";
import styles from "./CommandBanner.module.css";

/*
 * BANER DOWÓDCY (góra zakładki Player): portret frakcji w tle po lewej (ten sam łańcuch źródeł
 * co scena wyboru frakcji - `portraitCandidates`), tożsamość gracza, cytat frakcji, żetony
 * stołu (mówca, tyran, karty strategii, komunikaty frakcji - `HeaderTokens` z karty gracza)
 * oraz pozycje, które karta gracza miała tylko w swoim nagłówku (sąsiedzi, secondary do
 * podjęcia, przełom). Karta gracza pod spodem rysuje się bez nagłówka (`hideHeader`).
 */

/** Strips quotes pasted into the lore data (the component adds its own) and a leading dash. */
function cleanQuote(text: string | undefined): string | undefined {
  return text?.trim().replace(/^["“”„«»]+|["“”„«»]+$/g, "").trim() || undefined;
}

/** Portrait: first local source that loads; the last candidate (faction icon) is a small emblem. */
function BannerPortrait({ player }: { player: PlayerData }) {
  const candidates = useMemo(
    () => portraitCandidates({ id: player.faction, leaders: player.leaderIDs ?? [] }),
    [player.faction, player.leaderIDs],
  );
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [candidates]);
  if (index >= candidates.length) return null;
  const isIcon = index === candidates.length - 1;
  return (
    <div className={styles.portraitLayer} aria-hidden="true">
      <img
        key={candidates[index]}
        src={candidates[index]}
        alt=""
        className={isIcon ? styles.portraitIcon : styles.portrait}
        onError={() => setIndex((i) => i + 1)}
      />
    </div>
  );
}

/** Full faction lore in a window - read mid-game without leaving the table. */
function LoreButton({ faction, factionName }: { faction: string; factionName: string }) {
  const [opened, setOpened] = useState(false);
  const lore = getFactionLore(faction);
  const blocks = loreToBlocks(lore?.lore);
  if (blocks.length === 0) return null;
  const quote = cleanQuote(lore?.quote);
  const author = lore?.quoteAuthor?.trim().replace(/^[—–-]\s*/, "");
  return (
    <>
      <Button
        variant="subtle"
        size="xs"
        leftSection={<IconBook2 size={14} aria-hidden="true" />}
        onClick={() => setOpened(true)}
      >
        Lore
      </Button>
      <AppModal opened={opened} onClose={() => setOpened(false)} title={factionName} size="lg">
        <article className={styles.lore} lang="en">
          {quote && <blockquote className={styles.loreQuote}>{quoted(quote)}</blockquote>}
          {quote && author && <p className={styles.loreAuthor}>{attribution(author)}</p>}
          {blocks.map((block, i) =>
            block.kind === "heading" ? (
              <h3 key={i}>{block.text}</h3>
            ) : block.kind === "quote" ? (
              <blockquote key={i} className={styles.loreQuote}>
                {block.text}
              </blockquote>
            ) : (
              <p key={i} data-tone={block.tone}>
                {block.text}
              </p>
            ),
          )}
        </article>
      </AppModal>
    </>
  );
}

export function CommandBanner({
  player,
  subtitle,
  vpsToWin,
  rank,
  scouting,
}: {
  player: PlayerData;
  /** Phase · round · roles line under the name. */
  subtitle: string;
  vpsToWin: number;
  rank: number;
  /** Viewing another player than my own seat (Opponent Intel). */
  scouting: boolean;
}) {
  const showNeighbors = useSettingsStore((s) => s.settings.showPlayerAreaNeighborship);
  const fields = getPlayerCardLayoutFields(player);
  const lore = getFactionLore(player.faction);
  const quote = cleanQuote(lore?.quote);
  const author = lore?.quoteAuthor?.trim().replace(/^[—–-]\s*/, "");
  const breakthrough = player.breakthrough;

  return (
    <header className={styles.banner} aria-label="Commander">
      <BannerPortrait key={player.faction} player={player} />

      <div className={styles.body}>
        <div className={styles.identity}>
          <span className={styles.icon} aria-hidden="true">
            {player.faction ? <CircularFactionIcon faction={player.faction} size={40} /> : null}
          </span>
          <div className={styles.names}>
            <h2>
              {playerName(player)}
              {scouting && <span className={styles.intel}>Intel</span>}
            </h2>
            {fields.factionDisplayName !== playerName(player) && (
              <p className={styles.faction}>{fields.factionDisplayName}</p>
            )}
            <p className={styles.subtitle}>{subtitle}</p>
          </div>
          <div className={styles.vp} title={`${player.totalVps} of ${vpsToWin} victory points`}>
            <IconFlag size={16} aria-hidden="true" />
            <b>{player.totalVps}</b>
            <small>/ {vpsToWin} VP</small>
            <span className={styles.rank}>#{rank}</span>
          </div>
        </div>

        {quote && (
          <figure className={styles.quote}>
            <blockquote>{quoted(quote)}</blockquote>
            {author && <figcaption>{attribution(author)}</figcaption>}
          </figure>
        )}

        <div className={styles.status}>
          <HeaderTokens
            faction={player.faction}
            factionDisplayName={fields.factionDisplayName}
            playerId={player.discordId}
            isSpeaker={player.isSpeaker}
            isTyrant={fields.isTyrant}
            scs={player.scs}
            exhaustedSCs={player.exhaustedSCs}
          />
          {(player.unfollowedSCs ?? []).length > 0 && <NeedsToFollow values={player.unfollowedSCs} />}
          {showNeighbors && <Neighbors neighbors={player.neighbors ?? []} />}
          {breakthrough?.breakthroughId && (
            <span className={styles.breakthrough}>
            <Breakthrough
              breakthroughId={breakthrough.breakthroughId}
              exhausted={breakthrough.exhausted}
              tradeGoodsStored={breakthrough.tradeGoodsStored}
              unlocked={breakthrough.unlocked ?? false}
              flipped={breakthrough.flipped ?? false}
              strong={false}
              chipClassName={breakthroughStyles.headerChip}
            />
            </span>
          )}
          <span className={styles.spacer} />
          <LoreButton faction={player.faction} factionName={fields.factionDisplayName} />
        </div>
      </div>
    </header>
  );
}
