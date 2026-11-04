import type { ReactNode } from "react";
import { Box, Text } from "@/ds";
import { CardPoolData } from "@/entities/data/types";
import styles from "./CardPool.module.css";
import {
  ActionCardDeckCardBack,
  AgendaDeckCardBack,
  ExplorationDeckCardBack,
  PublicObjectiveDeckCardBack,
  RelicDeckCardBack,
  SecretObjectiveDeckCardBack,
} from "@/domains/cards/components/PoolDeckCardBack";

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

/** Deck card backs, grouped by kind; click a deck to browse its full pool. */
function CardPool({ cardPool }: Props) {
  if (!cardPool) {
    return <Text className={styles.empty}>No card pool data available</Text>;
  }

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
        <Slot label="Action">
          <ActionCardDeckCardBack count={cardPool.actionCardDeckSize} />
        </Slot>
        <Slot label="Agenda">
          <AgendaDeckCardBack count={cardPool.agendaDeckSize} />
        </Slot>
        <Slot label="Relics">
          <RelicDeckCardBack count={cardPool.relicDeckSize} />
        </Slot>
      </Group>

      <Group title="Exploration">
        <Slot label="Cultural">
          <ExplorationDeckCardBack type="Cultural" />
        </Slot>
        <Slot label="Industrial">
          <ExplorationDeckCardBack type="Industrial" />
        </Slot>
        <Slot label="Hazardous">
          <ExplorationDeckCardBack type="Hazardous" />
        </Slot>
        <Slot label="Frontier">
          <ExplorationDeckCardBack type="Frontier" />
        </Slot>
      </Group>
    </Box>
  );
}

export default CardPool;
