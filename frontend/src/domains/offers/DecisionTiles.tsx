import { createContext, useContext, useEffect, useMemo } from "react";
import { IconCheck, IconEye } from "@tabler/icons-react";
import type { ActionCardOption } from "@/api/useActionCard";
import { getColorAlias } from "@/entities/lookup/colors";
import { Stepper } from "@/shared/ui/Stepper/Stepper";
import { Unit } from "@/shared/ui/Unit";
import { asyncOfBase } from "@/domains/movement/routeTypes";
import { ComponentInfoButton, type ComponentRef } from "@/domains/cards/components/ComponentInfo";
import { useGameData } from "@/state/useGameContext";
import { clearMapMarks, mapHits, mapRefKeys, showOnMap } from "@/domains/search/mapPeek";
import type { SearchKey } from "@/domains/search/searchKeys";
import type { OptionKind } from "./optionKinds";
import {
  DescribedOptionBody,
  describeOption,
  PlayerOptionBody,
  TechOptionBody,
} from "./DecisionPickers";
import styles from "./DecisionFields.module.css";

/*
 * Elementy wspólne pól decyzji (``DecisionFields``, ``GroupedMapField``): kafelek opcji z grafiką
 * (jednostka, planeta, kość, technologia, gracz, komponent gry), nagłówek pola i licznik −/+.
 */

type Meta = Record<string, unknown>;

export function metaOf(option: ActionCardOption): Meta {
  return option.meta ?? {};
}

/** Sprite jednostki z ``meta`` opcji (typ, kolor i frakcja gracza), opcjonalnie z liczbą sztuk. */
function UnitSprite({ meta, count = 0 }: { meta: Meta; count?: number }) {
  if (typeof meta.unit !== "string") return null;
  return (
    <span className={styles.sprite} aria-hidden="true">
      <Unit
        unitType={asyncOfBase(meta.unit)}
        colorAlias={getColorAlias(typeof meta.color === "string" ? meta.color : undefined)}
        faction={typeof meta.faction === "string" ? meta.faction : undefined}
        scaleSprite
      />
      {count > 1 && <i className={styles.count}>×{count}</i>}
    </span>
  );
}

/**
 * Stos jednakowych jednostek (``optionKinds.stacksOf``) jako jeden licznik −/+: sprite, nazwa i
 * ile sztuk wybrano. ``value`` = liczba wybranych opcji stosu (bierzemy je po kolei).
 */
export function UnitStackStepper({
  options,
  value,
  max,
  disabled,
  onChange,
}: {
  options: ActionCardOption[];
  value: number;
  /** Najwięcej sztuk z tego stosu (rozmiar stosu i limit całego pola). */
  max: number;
  disabled: boolean;
  onChange: (count: number) => void;
}) {
  const first = options[0];
  if (!first) return null;
  const { title } = splitLabel(first.label.replace(/\s+#\d+$/, ""));
  return (
    <div className={styles.unitStack} data-picked={value > 0 || undefined}>
      <UnitSprite meta={metaOf(first)} />
      <span className={styles.stackCtl}>
        <Stepper label={title} value={value} min={0} max={max} disabled={disabled} onChange={onChange} />
      </span>
    </div>
  );
}

/** „Nazwa - dopisek” z backendu → tytuł kafelka i mniejszy podpis. */
export function splitLabel(label: string): { title: string; caption: string } {
  const at = label.indexOf(" - ");
  if (at < 0) return { title: label, caption: "" };
  return { title: label.slice(0, at), caption: label.slice(at + 3) };
}

export function OptionBody({ option }: { option: ActionCardOption }) {
  const meta = metaOf(option);
  if (typeof meta.die === "number") {
    const hitsOn = typeof meta.hitsOn === "number" ? meta.hitsOn : 11;
    const hit = meta.die >= hitsOn;
    return (
      <>
        <span className={styles.die} data-hit={hit || undefined} aria-hidden="true">
          {meta.die}
        </span>
        <span className={styles.optText}>
          <b>{splitLabel(option.label.split(":")[0] ?? option.label).title}</b>
          <small>{hit ? "hit" : `miss (hits on ${hitsOn})`}</small>
        </span>
      </>
    );
  }
  const { title, caption } = splitLabel(option.label);
  if (typeof meta.unit === "string") {
    return (
      <>
        <UnitSprite meta={meta} count={typeof meta.count === "number" ? meta.count : 0} />
        <span className={styles.optText}>
          <b>{title}</b>
          {caption && <small>{caption}</small>}
        </span>
      </>
    );
  }
  if (typeof meta.planet === "string") {
    const value = typeof meta.value === "number" ? meta.value : 0;
    return (
      <>
        <span
          className={styles.value}
          data-kind={meta.valueKind === "influence" ? "influence" : "resources"}
          aria-hidden="true"
        >
          {value}
        </span>
        <span className={styles.optText}>
          <b>{title.replace(/\s*\(\d+\)$/, "")}</b>
          <small>{caption || (meta.valueKind === "influence" ? "influence" : "resources")}</small>
        </span>
      </>
    );
  }
  return (
    <span className={styles.optText}>
      <b>{title}</b>
      {caption && <small>{caption}</small>}
    </span>
  );
}

export function Tile({
  option,
  selected,
  disabled,
  multi,
  onClick,
  kind,
}: {
  option: ActionCardOption;
  selected: boolean;
  disabled: boolean;
  multi: boolean;
  onClick: () => void;
  /** Rodzaj wyboru (``optionKinds``) i cel tej opcji - graficzna treść kafelka. */
  kind?: { kind: OptionKind; target: string };
}) {
  const meta = metaOf(option);
  const shape = typeof meta.die === "number" ? "die" : undefined;
  const mapRef = useMapRef(option);
  const idMap = useGameData()?.strategyCardIdMap;
  const described = kind ? null : describeOption(option, idMap);
  // Technologia z odnośnika (``tech:<id>``, „keep”) wygląda jak każdy kafelek technologii.
  const techId =
    kind?.kind === "technology"
      ? kind.target
      : described?.ref.kind === "tech"
        ? described.ref.id
        : null;
  // Co pokazać pod ⓘ (klik = pełna karta): komponent z opisem albo technologia.
  const infoRef: ComponentRef | null = techId
    ? { kind: "tech", id: techId }
    : (described?.ref ?? null);
  const tile = (
    <button
      type="button"
      className={styles.tile}
      data-shape={shape}
      aria-pressed={selected}
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={mapRef ? () => showOnMap(mapRef) : undefined}
      onMouseLeave={mapRef ? clearMapMarks : undefined}
    >
      {techId ? (
        <TechOptionBody option={option} techId={techId} />
      ) : kind?.kind === "player" ? (
        <PlayerOptionBody option={option} playerId={kind.target} />
      ) : described ? (
        <DescribedOptionBody
          option={option}
          hint={described.hint}
          brief={described.ref.kind === "strategy"}
        />
      ) : (
        <OptionBody option={option} />
      )}
      {multi && (
        <span className={styles.check} aria-hidden="true">
          {selected && <IconCheck size={11} />}
        </span>
      )}
    </button>
  );
  if (!mapRef && !infoRef) return tile;
  const name = described?.hint.name || splitLabel(option.label).title;
  return (
    <span className={styles.tileWrap}>
      {tile}
      <span className={styles.tileActions}>
        {/* Klik: pełna karta komponentu (jak chip w panelu gracza) - działa też na dotyku. */}
        {infoRef && <ComponentInfoButton componentRef={infoRef} name={name} />}
        {/* Najechanie: okno prześwituje i widać cel na mapie; klik: mapa przewija się do celu. */}
        {mapRef && (
          <button
            type="button"
            className={styles.locate}
            aria-label={`Show ${name} on the map`}
            title="Hover to see it on the map, click to centre the map on it"
            onMouseEnter={() => showOnMap(mapRef, { peek: true })}
            onMouseLeave={clearMapMarks}
            onFocus={() => showOnMap(mapRef, { peek: true })}
            onBlur={clearMapMarks}
            onClick={() => showOnMap(mapRef, { peek: true, jump: true })}
          >
            <IconEye size={13} aria-hidden="true" />
          </button>
        )}
      </span>
    </span>
  );
}

/**
 * Klucze mapy opcji, gdy wskazuje planetę albo system leżący na planszy (inaczej ``null``).
 * Sprawdzamy DOM mapy (znaczniki wyszukiwarki), więc nie trzeba znać formatu każdego wejścia.
 */
function useMapRef(option: ActionCardOption) {
  // Podpis kluczy (string) jako zależność: nowa, ale równa lista nie liczy DOM od nowa.
  const signature = mapRefKeys(option.value, option.meta).join("|");
  const keys = useMemo(() => {
    if (!signature) return null;
    const list = signature.split("|") as SearchKey[];
    return mapHits(list).length > 0 ? list : null;
  }, [signature]);
  // Okno zamknięte w trakcie najechania nie zostawia podświetlenia ani prześwitu.
  useEffect(() => (keys ? clearMapMarks : undefined), [keys]);
  return keys;
}

/** Tytuł otaczającej ramy: etykieta pola równa tytułowi nie jest powtarzana (U4, Z12). */
export const FrameTitleContext = createContext<string | null>(null);

export function FieldHead({ label, hint, note }: { label: string; hint?: string; note?: string }) {
  const frameTitle = useContext(FrameTitleContext);
  const repeats = frameTitle != null && label.trim().toLowerCase() === frameTitle.trim().toLowerCase();
  return (
    <div className={styles.head}>
      {!repeats && <span className={styles.label}>{label}</span>}
      {note && <span className={styles.note}>{note}</span>}
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}
