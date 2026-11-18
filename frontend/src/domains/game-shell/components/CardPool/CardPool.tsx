import { useMemo, type ReactNode } from "react";
import { Box, Text } from "@/ds";
import { CardPoolData } from "@/entities/data/types";
import styles from "./CardPool.module.css";
import {
  AgendaDeckCardBack,
  PublicObjectiveDeckCardBack,
  RelicDeckCardBack,
  SecretObjectiveDeckCardBack,
} from "@/domains/cards/components/PoolDeckCardBack";
import {
  DeckBack,
  PileSlot,
  PurgedPile,
} from "@/domains/cards/components/DeckInspector/DeckInspector";
import { deckSpecs } from "@/domains/cards/model/deckPiles";

type Props = {
  cardPool?: CardPoolData;
};

/** One labelled deck slot: a card back with its name underneath. */
function Slot({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box className={styles.slot}>
      {children}
      <Text className={styles.slotLabel}>{label}</Text>
    </Box>
  );
}

/** A titled band of deck slots. */
function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Box className={styles.group}>
      <Text className={styles.groupTitle}>{title}</Text>
      <Box className={styles.row}>{children}</Box>
    </Box>
  );
}

/**
 * Deck card backs, grouped by kind. Exploration and action decks track the REAL game
 * state: the count is what is LEFT, a drawn card is gone from the deck, and each deck has
 * its own discard pile plus one shared purge pile. Click a deck/pile to browse it.
 */
function CardPool({ cardPool }: Props) {
  const specs = useMemo(() => (cardPool ? deckSpecs(cardPool) : []), [cardPool]);
  if (!cardPool) {
    return <Text className={styles.empty}>No card pool data available</Text>;
  }
  const bySpec = (key: string) => specs.find((s) => s.key === key);
  const action = bySpec("action");
  const explore = specs.filter((s) => s.kind === "explore");

  return (
    <Box className={styles.pool}>
      <Group title="Objectives">
        <Slot label="Stage I">
          <PublicObjectiveDeckCardBack stage={1} />
        </Slot>
        <Slot label="Stage II">
          <PublicObjectiveDeckCardBack stage={2} />
        </Slot>
        <Slot label="Secrets">
          <SecretObjectiveDeckCardBack />
        </Slot>
      </Group>

      <Group title="Decks">
        {action && (
          <Slot label="Action">
            <DeckBack spec={action} />
          </Slot>
        )}
        <Slot label="Agenda">
          <AgendaDeckCardBack count={cardPool.agendaDeckSize} />
        </Slot>
        <Slot label="Relics">
          <RelicDeckCardBack count={cardPool.relicDeckSize} />
        </Slot>
      </Group>

      <Group title="Exploration">
        {explore.map((spec) => (
          <Slot key={spec.key} label={spec.label}>
            <DeckBack spec={spec} />
          </Slot>
        ))}
      </Group>

      <Group title="Discard piles">
        {action && (
          <Slot label="Action">
            <PileSlot spec={action} tab="discard" />
          </Slot>
        )}
        {explore.map((spec) => (
          <Slot key={spec.key} label={spec.label}>
            <PileSlot spec={spec} tab="discard" />
          </Slot>
        ))}
      </Group>

      <Group title="Purged">
        <Slot label="All decks">
          <PurgedPile specs={specs} />
        </Slot>
      </Group>
    </Box>
  );
}

export default CardPool;
