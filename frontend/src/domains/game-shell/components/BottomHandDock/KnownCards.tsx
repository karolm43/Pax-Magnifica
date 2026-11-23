import type { ReactNode } from "react";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { KnownAgenda } from "@/domains/player/components/KnownAgenda";
import { ScoredSecret } from "@/domains/player/components/ScoredSecret";
import { PromissoryNote } from "@/domains/player/components/PromissoryNote";
import type { GamePeek, PlayerData } from "@/entities/data/types";
import styles from "./BottomHandDock.module.css";

type Props = {
  /** Znane karty od góry talii agend (kolejność) i od spodu (ostatnia = sam spód). */
  agendaTop: string[];
  agendaBottom: string[];
  /** Tajne cele innych graczy pokazane przez Extreme Duress: {gracz: [cele]}. */
  revealedSecrets: Record<string, string[]>;
  maban: GamePeek | null;
  players: PlayerData[];
};

/** Wiedza o talii agend: własna (Insider Information, Politics) + M'aban, bez powtórzeń. */
export function knownAgendaPlaces(
  top: string[],
  bottom: string[],
  maban: GamePeek | null,
): { id: string; place: string }[] {
  const known = [...top];
  if (known.length === 0 && maban?.agendaTop) known.push(maban.agendaTop);
  const fromBottom = [...bottom];
  if (fromBottom.length === 0 && maban?.agendaBottom) fromBottom.push(maban.agendaBottom);
  const places = known.map((id, index) => ({ id, place: `Top ${index + 1}` }));
  // Spód liczony od dołu: ostatnia karta to „Bottom”, przedostatnia „Bottom 2”.
  const reversed = [...fromBottom].reverse();
  reversed.forEach((id, index) => {
    places.push({ id, place: index === 0 ? "Bottom" : `Bottom ${index + 1}` });
  });
  return places;
}

function Group({ title, faction, children }: { title: string; faction?: string; children: ReactNode }) {
  return (
    <section className={styles.knownGroup} aria-label={title}>
      <span className={styles.knownTitle}>
        {faction && <CircularFactionIcon faction={faction} size={16} />}
        {title}
      </span>
      <div className={styles.knownChips}>{children}</div>
    </section>
  );
}

/**
 * Ukryte informacje, które gracz POZNAŁ (karty i zdolności „look at…”): te same chipy co w
 * panelu gracza, opis po kliknięciu. Wiedza o talii agend trwa, aż talia się zmieni
 * (RULES.md 53.5.a1) - nie znika po fazie agendy.
 */
export function KnownCards({ agendaTop, agendaBottom, revealedSecrets, maban, players }: Props) {
  const nameOf = (pid: string) => {
    const player = players.find((p) => p.discordId === pid);
    return { name: player?.flexibleDisplayName || player?.faction || pid, faction: player?.faction };
  };
  const agendas = knownAgendaPlaces(agendaTop, agendaBottom, maban);
  const groups: ReactNode[] = [];
  if (agendas.length > 0) {
    groups.push(
      <Group key="agenda" title="Agenda deck you know">
        {agendas.map(({ id, place }) => (
          <KnownAgenda key={`${place}-${id}`} agendaId={id} place={place} />
        ))}
      </Group>,
    );
  }
  for (const [owner, ids] of Object.entries(revealedSecrets)) {
    const who = nameOf(owner);
    groups.push(
      <Group key={`so-${owner}`} title={`Secret objectives of ${who.name}`} faction={who.faction}>
        {ids.length > 0 ? (
          ids.map((id) => <ScoredSecret key={id} secretId={id} variant="unscored" />)
        ) : (
          <span className={styles.knownEmpty}>none</span>
        )}
      </Group>,
    );
  }
  for (const [owner, notes] of Object.entries(maban?.neighbors ?? {})) {
    const who = nameOf(owner);
    groups.push(
      <Group key={`pn-${owner}`} title={`Promissory notes of ${who.name}`} faction={who.faction}>
        {notes.length > 0 ? (
          notes.map((id) => <PromissoryNote key={id} promissoryNoteId={id} />)
        ) : (
          <span className={styles.knownEmpty}>none</span>
        )}
      </Group>,
    );
  }
  if (groups.length === 0) return null;
  return (
    <div className={styles.known} aria-label="What you know">
      {groups}
    </div>
  );
}
