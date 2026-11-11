import { useEffect, useMemo, useState } from "react";
import { IconArrowRight, IconX } from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { useMapPick } from "@/domains/strategy/mapPick";
import { usePlayerLook } from "@/domains/invasion/invasionUi";
import { Unit } from "@/shared/ui/Unit";
import type { FormValue } from "@/api/useActionCard";
import type { OfferView } from "@/api/useOffers";
import styles from "./TransitDiodesPicker.module.css";

/** Transit Diodes: "up to 4 of your ground forces" (tyle slotów ma formularz silnika). */
const SLOTS = 4;
const NONE = "none";

type Stack = {
  id: string;
  asyncId: string;
  baseType: string;
  count: number;
  position: string;
  placeName: string;
};
type Target = { id: string; planet: string; name: string; position: string };
type Pick = { stack: string; dest: string | null };

type Meta = Record<string, string | number>;

function metaOf<T>(
  options: { id: string; meta?: Record<string, unknown> }[],
  map: (id: string, m: Meta) => T,
): T[] {
  return options.filter((o) => o.id !== NONE && o.meta).map((o) => map(o.id, (o.meta ?? {}) as Meta));
}

/**
 * Graficzny wybór Transit Diodes (jak ruch): najpierw klikasz siły naziemne do PODNIESIENIA
 * (do 4), potem wskazujesz, GDZIE je położyć - klikiem w podświetloną na mapie własną planetę
 * albo w jej chip. Wynik to te same pola co w formularzu silnika (unit1..4 / to1..4), a silnik
 * i tak waliduje wybór.
 */
export function TransitDiodesPicker({
  offer,
  disabled,
  onChange,
}: {
  offer: OfferView;
  disabled: boolean;
  onChange: (values: Record<string, FormValue>, complete: boolean) => void;
}) {
  const gameData = useGameData();
  const look = usePlayerLook();
  const player = gameData?.playerData?.find((p) => p.discordId === offer.player_id);
  const faction = player?.faction ?? "";
  const mine = look(faction);

  const stacks = useMemo<Stack[]>(() => {
    const input = offer.inputs.find((i) => i.key === "unit1");
    if (!input || input.kind !== "choice") return [];
    return metaOf(input.options, (id, m) => ({
      id,
      asyncId: String(m.asyncId ?? ""),
      baseType: String(m.baseType ?? ""),
      count: Number(m.count ?? 0),
      position: String(m.position ?? ""),
      placeName: String(m.placeName ?? ""),
    }));
  }, [offer.inputs]);
  const targets = useMemo<Target[]>(() => {
    const input = offer.inputs.find((i) => i.key === "to1");
    if (!input || input.kind !== "choice") return [];
    return metaOf(input.options, (id, m) => ({
      id,
      planet: String(m.planet ?? ""),
      name: String(m.name ?? m.planet ?? ""),
      position: String(m.position ?? ""),
    }));
  }, [offer.inputs]);

  const [picks, setPicks] = useState<Pick[]>([]);
  const [focus, setFocus] = useState<number | null>(null);

  const pickedOf = (stackId: string) => picks.filter((p) => p.stack === stackId).length;
  const stackOf = (id: string) => stacks.find((s) => s.id === id);
  const targetOf = (id: string | null) => targets.find((t) => t.id === id) ?? null;

  const addPick = (stack: Stack) => {
    if (disabled || picks.length >= SLOTS || pickedOf(stack.id) >= stack.count) return;
    setPicks((prev) => [...prev, { stack: stack.id, dest: null }]);
    setFocus(picks.length);
  };
  const removePick = (index: number) => {
    setPicks((prev) => prev.filter((_, i) => i !== index));
    setFocus(null);
  };

  // Cel dla klikniętej planety: wskazana pozycja, a bez niej pierwsza bez miejsca docelowego.
  const place = (targetId: string) => {
    if (disabled) return;
    setPicks((prev) => {
      const index =
        focus !== null && focus < prev.length
          ? focus
          : prev.findIndex((p) => p.dest === null);
      if (index < 0) return prev;
      const next = prev.map((p, i) => (i === index ? { ...p, dest: targetId } : p));
      setFocus(next.findIndex((p, i) => i > index && p.dest === null));
      return next;
    });
  };
  const placeByPlanet = (planet: string) => {
    const target = targets.find((t) => t.planet === planet);
    if (target) place(target.id);
  };

  // Własne planety podświetlone NA MAPIE; klik kładzie wskazaną jednostkę.
  const focused = focus !== null ? picks[focus] : undefined;
  useMapPick("planet", picks.length > 0 ? targets.map((t) => t.planet) : [], placeByPlanet, {
    hue: `rgb(${mine.rgb})`,
    selected: targetOf(focused?.dest ?? null)?.planet ?? null,
    enabled: !disabled,
  });

  const complete = picks.length > 0 && picks.every((p) => p.dest !== null);
  useEffect(() => {
    const values: Record<string, FormValue> = {};
    for (let slot = 1; slot <= SLOTS; slot += 1) {
      const pick = picks[slot - 1];
      const done = pick !== undefined && pick.dest !== null;
      values[`unit${slot}`] = done ? pick.stack : NONE;
      values[`to${slot}`] = done ? (pick.dest ?? NONE) : NONE;
    }
    onChange(values, complete);
    // onChange pochodzi z rodzica (stabilny setter + obliczenia) - reagujemy tylko na wybór.
  }, [picks]);

  const sprite = (asyncId: string) => (
    <span className={styles.sprite}>
      <Unit unitType={asyncId} colorAlias={mine.colorAlias} faction={faction} scaleSprite />
    </span>
  );

  if (stacks.length === 0) {
    return <p className={styles.empty}>You have no ground forces to move.</p>;
  }

  return (
    <div className={styles.root}>
      <section aria-label="Pick up ground forces">
        <h5 className={styles.step}>
          <b>1</b> Pick up <small>{picks.length}/{SLOTS}</small>
        </h5>
        <div className={styles.stacks}>
          {stacks.map((stack) => {
            const n = pickedOf(stack.id);
            const full = picks.length >= SLOTS || n >= stack.count;
            return (
              <button
                key={stack.id}
                type="button"
                className={styles.stack}
                data-picked={n > 0 || undefined}
                disabled={disabled || full}
                onClick={() => addPick(stack)}
                title={`${stack.baseType} on ${stack.placeName} (${stack.position}): click to pick up`}
              >
                {sprite(stack.asyncId)}
                <span className={styles.stackText}>
                  <b>{stack.count - n}×</b>
                  <small>
                    {stack.placeName} · {stack.position}
                  </small>
                </span>
                {n > 0 && <i className={styles.badge}>{n}</i>}
              </button>
            );
          })}
        </div>
      </section>

      <section aria-label="Place ground forces">
        <h5 className={styles.step}>
          <b>2</b> Place on one of your planets
        </h5>
        {picks.length === 0 ? (
          <p className={styles.hint}>Pick up to {SLOTS} ground forces first.</p>
        ) : (
          <ul className={styles.queue}>
            {picks.map((pick, i) => {
              const stack = stackOf(pick.stack);
              const target = targetOf(pick.dest);
              return (
                <li
                  key={`${pick.stack}-${i}`}
                  className={styles.row}
                  data-focus={focus === i || undefined}
                  data-done={pick.dest !== null || undefined}
                >
                  <button
                    type="button"
                    className={styles.rowMain}
                    onClick={() => setFocus(i)}
                    aria-pressed={focus === i}
                    title="Select, then click a planet on the map or below"
                  >
                    {stack && sprite(stack.asyncId)}
                    <small>
                      {stack?.placeName} · {stack?.position}
                    </small>
                    <IconArrowRight size={13} aria-hidden="true" />
                    <b>{target ? `${target.name}` : "choose a planet"}</b>
                  </button>
                  <button
                    type="button"
                    className={styles.remove}
                    onClick={() => removePick(i)}
                    aria-label="Put back"
                    title="Put back"
                  >
                    <IconX size={13} aria-hidden="true" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {picks.length > 0 && (
          <div className={styles.planets} role="group" aria-label="Your planets">
            {targets.map((target) => (
              <button
                key={target.id}
                type="button"
                className={styles.planet}
                disabled={disabled}
                data-chosen={focused?.dest === target.id || undefined}
                onClick={() => place(target.id)}
                title="Your planets are highlighted on the map too"
              >
                {target.name}
                <small>{target.position}</small>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
