import { useMemo, type CSSProperties } from "react";
import type { ActionCardOption } from "@/api/useActionCard";
import { Tooltip } from "@/ds";
import { TechCard } from "@/domains/cards/components/TechCard/TechCard";
import {
  refFromMeta,
  type ComponentKind,
  type ComponentRef,
} from "@/domains/cards/components/ComponentInfo";
import { COLOR_HUE, COLOR_ICON, type TechColor } from "@/domains/technology/techModel";
import { getPlanetData } from "@/entities/lookup/planets";
import { getTechData } from "@/entities/lookup/tech";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { playerName, playerRgb } from "@/domains/strategy/PlayerChip";
import { useGameData } from "@/state/useGameContext";
import {
  HintBody,
  hintFor,
  type Hint,
} from "@/domains/game-shell/components/ActivityPanel/Named";
import type { OptionLookups } from "./optionKinds";
import styles from "./DecisionFields.module.css";

/*
 * Graficzne opcje wyboru wspólne dla wszystkich formularzy (``DecisionField``): technologia jako
 * kafelek technologii (kolor + pełna karta po najechaniu), gracz jako ikona frakcji, a planeta /
 * system jako wybór KLIKNIĘCIEM NA MAPIE (``useMapPick``) - jak przy kartach strategii.
 */

/** Słowniki do rozpoznania opcji (dane gry + wbudowane dane AsyncTI4). */
export function useOptionLookups(): OptionLookups {
  const gameData = useGameData();
  const players = gameData?.playerData;
  const tiles = gameData?.tiles;
  return useMemo(() => {
    const ids = new Set((players ?? []).map((p) => p.discordId).filter(Boolean));
    return {
      isTech: (id) => getTechData(id) !== undefined,
      isPlayer: (id) => ids.has(id),
      isPlanet: (id) => getPlanetData(id) !== undefined,
      isSystem: (pos) => tiles?.[pos] !== undefined,
    };
  }, [players, tiles]);
}

const TECH_COLORS = new Set<string>(["PROPULSION", "BIOTIC", "CYBERNETIC", "WARFARE"]);

function techColor(id: string): TechColor | null {
  const type = getTechData(id)?.types.find((t) => TECH_COLORS.has(t.toUpperCase()));
  return type ? (type.toUpperCase() as TechColor) : null;
}

/** Treść kafelka technologii: ikona koloru + nazwa; pełna karta po najechaniu. */
export function TechOptionBody({ option, techId }: { option: ActionCardOption; techId: string }) {
  const tech = getTechData(techId);
  const color = techColor(techId);
  const at = option.label.indexOf(" - ");
  const caption = at >= 0 ? option.label.slice(at + 3) : "";
  return (
    <Tooltip
      label={<TechCard techId={techId} />}
      openDelay={350}
      position="right"
      multiline
      events={{ hover: true, focus: false, touch: false }}
    >
      <span
        className={styles.techOpt}
        style={{ "--tc": color ? COLOR_HUE[color] : "170 178 196" } as CSSProperties}
      >
        {color ? (
          <img src={COLOR_ICON[color]} alt="" width={16} height={16} aria-hidden="true" />
        ) : (
          <span className={styles.techUpgrade} aria-hidden="true">U</span>
        )}
        <span className={styles.optText}>
          <b>{tech?.name ?? option.label}</b>
          {caption && <small>{caption}</small>}
          {/* Zawsze widać, CO technologia robi (pełna karta po najechaniu). */}
          {tech?.text && <span className={styles.descr}>{tech.text}</span>}
        </span>
      </span>
    </Tooltip>
  );
}

/** Komponenty gry rozpoznawane po gołym id w ``value`` (cel, agenda, karta, notka, lider…). */
const DESCRIBED_KINDS: ComponentKind[] = [
  "objective",
  "agenda",
  "actionCard",
  "promissory",
  "leader",
  "explore",
  "relic",
  "breakthrough",
];

export type Described = { ref: ComponentRef; hint: Hint };

/**
 * Komponent gry, którego dotyczy opcja, z opisem - albo ``null``. Najpierw jawny odnośnik
 * silnika (``meta.ref``: karta strategii po inicjatywie, wartości z prefiksem), potem gołe id
 * w ``value``. ``idMap`` = kanoniczne warianty kart strategii z backendu.
 */
export function describeOption(
  option: ActionCardOption,
  idMap?: Record<number, string>,
): Described | null {
  const fromMeta = refFromMeta(option.meta);
  if (fromMeta) {
    const hint = hintFor(fromMeta.kind, fromMeta.id, { idMap });
    return hint ? { ref: fromMeta, hint } : null;
  }
  const value = typeof option.value === "string" ? option.value : null;
  if (!value) return null;
  for (const kind of DESCRIBED_KINDS) {
    const hint = hintFor(kind, value);
    if (hint) return { ref: { kind, id: value }, hint };
  }
  return null;
}

/**
 * Treść kafelka komponentu gry (karta strategii, cel, agenda, relikt, karta akcji…): nazwa,
 * rodzaj i CAŁY tekst zasady (każdy akapit), pełny opis po najechaniu, a pełna karta pod
 * przyciskiem ⓘ kafelka. ``brief`` (karty strategii - decyzja użytkownika): sama nazwa i
 * podpis, bez drobnego tekstu primary/secondary - ten jest w okienku ⓘ i w podpowiedzi.
 */
export function DescribedOptionBody({
  option,
  hint,
  brief = false,
}: {
  option: ActionCardOption;
  hint: Hint;
  brief?: boolean;
}) {
  const at = option.label.indexOf(" - ");
  const caption = at >= 0 ? option.label.slice(at + 3) : hint.meta;
  return (
    <Tooltip
      label={<HintBody hint={hint} />}
      openDelay={300}
      position="right"
      multiline
      maw={340}
      events={{ hover: true, focus: false, touch: false }}
    >
      <span className={styles.optText}>
        <b>{hint.name || option.label}</b>
        {caption && <small>{caption}</small>}
        {!brief && hint.lines.map((line, index) => (
          <span key={index} className={styles.descr}>
            {line}
          </span>
        ))}
      </span>
    </Tooltip>
  );
}

/**
 * Treść kafelka gracza: ikona frakcji w obwódce koloru gracza (jak ``PlayerChip`` w oknach kart
 * strategii) + nazwa w jego kolorze; podpis = co się stanie, gdy etykieta silnika mówi więcej
 * niż samo imię („Replenish X's commodities”).
 */
export function PlayerOptionBody({ option, playerId }: { option: ActionCardOption; playerId: string }) {
  const gameData = useGameData();
  const player = gameData?.playerData?.find((p) => p.discordId === playerId);
  const name = player ? playerName(player) : option.label;
  const at = option.label.indexOf(" - ");
  const caption =
    at >= 0 ? option.label.slice(at + 3) : option.label !== name && option.label !== playerId ? option.label : "";
  return (
    <span className={styles.playerOpt} style={{ "--pc": playerRgb(player?.color) } as CSSProperties}>
      <span className={styles.playerRing} aria-hidden="true">
        {player?.faction && <CircularFactionIcon faction={player.faction} size={22} />}
      </span>
      <span className={styles.optText}>
        <b className={styles.playerName}>{name}</b>
        {caption && <small>{caption}</small>}
      </span>
    </span>
  );
}
