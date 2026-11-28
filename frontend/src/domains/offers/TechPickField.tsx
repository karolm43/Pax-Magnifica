import { useMemo, useState } from "react";
import type { ActionCardInput, ActionCardOption, FormValue } from "@/api/useActionCard";
import { TechnologyOverlay } from "@/domains/technology/TechnologyOverlay";
import type { ResearchOptions, TechColor, TechRow } from "@/domains/technology/techModel";
import { getTechData } from "@/entities/lookup/tech";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import type { Classified } from "./optionKinds";
import { FieldHead, pickNote, Tile } from "./DecisionTiles";
import styles from "./DecisionFields.module.css";

/*
 * Wybór TECHNOLOGII w formularzu decyzji (decyzja użytkownika: nigdy lista technologii) - to
 * samo okno drzewa co badanie (``TechnologyOverlay``) w trybie „gain”: legalne opcje są
 * „available”, posiadane technologie gracza widać jako „owned” (kontekst), reszta nie istnieje.
 * W oknie formularza zostają tylko wybrane technologie (kafelek z ×) i przycisk otwarcia drzewa.
 * Wartość pola to id opcji - silnik waliduje wybór jak dotąd.
 */

const TYPE_COLOR: Record<string, TechColor> = {
  PROPULSION: "PROPULSION",
  BIOTIC: "BIOTIC",
  CYBERNETIC: "CYBERNETIC",
  WARFARE: "WARFARE",
};
// Litery prerekwizytów AsyncTI4: B niebieski, G zielony, Y żółty, R czerwony.
const REQ_COLOR: Record<string, TechColor> = {
  B: "PROPULSION",
  G: "BIOTIC",
  Y: "CYBERNETIC",
  R: "WARFARE",
};

/** Wiersz drzewa z danych statycznych technologii (bez danych silnika o skipach/płatności). */
export function techRowOf(techId: string, status: TechRow["status"]): TechRow | null {
  const tech = getTechData(techId);
  if (!tech) return null;
  const color = tech.types.map((t) => TYPE_COLOR[t.toUpperCase()]).find(Boolean) ?? null;
  const prerequisites = [...(tech.requirements ?? "")]
    .map((letter) => REQ_COLOR[letter.toUpperCase()])
    .filter((c): c is TechColor => c !== undefined);
  return {
    id: techId,
    name: tech.name,
    color,
    unitUpgrade: tech.types.some((t) => t.toUpperCase() === "UNITUPGRADE"),
    faction: tech.faction ?? null,
    baseUpgrade: tech.baseUpgrade ?? null,
    prerequisites,
    missing: {},
    status,
  };
}

/** Opcje okna drzewa dla wyboru z formularza: tylko ``allowed`` do wzięcia, bez płatności. */
export function pickTreeOptions(allowed: string[], owned: string[]): ResearchOptions {
  const keep = new Set(allowed);
  const tree = [
    ...allowed.map((id) => techRowOf(id, "available")),
    ...owned.filter((id) => !keep.has(id)).map((id) => techRowOf(id, "owned")),
  ].filter((row): row is TechRow => row !== null);
  return {
    tree,
    ownedColors: {},
    specialties: {},
    aida: false,
    relicSkips: [],
    infantrySkips: [],
    paidSkips: [],
    planets: {},
    tradeGoods: 0,
    tradeGoodValue: 1,
    tradeGoodsOnly: false,
    cost: 0,
    researched: [],
    breakthrough: null,
    discount: 0,
    compoundPlanets: {},
    asPrimary: false,
    second: null,
    gain: { mandatory: false, tokenPool: null, tokens: 0, note: "" },
    propagation: false,
  };
}

export function TechPickField({
  input,
  classified,
  value,
  disabled,
  onChange,
}: {
  input: Extract<ActionCardInput, { kind: "choice" | "multi" }>;
  classified: Classified;
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (value: FormValue) => void;
}) {
  const me = useDeskPlayer();
  const [open, setOpen] = useState(false);
  const multi = input.kind === "multi";
  const picked = multi ? (Array.isArray(value) ? value : []) : typeof value === "string" ? [value] : [];
  // Opcja → technologia i odwrotnie (opcja może mieć inne id niż technologia: „keep”, „tech:x”).
  const byTech = useMemo(() => {
    const map = new Map<string, string>();
    for (const [optionId, techId] of classified.targets) map.set(techId, optionId);
    return map;
  }, [classified]);
  const pickedOptions = input.options.filter((o) => picked.includes(o.id));
  const loose = input.options.filter((o) => !classified.targets.has(o.id));
  const room = multi ? input.max - picked.length : 1;
  // Formularz decyzji widzi tylko decydujący - to gracz przy biurku.
  const rgb = me?.color ? resolvePrimaryRgb(me.color) : undefined;
  const allowed = [...classified.targets.entries()]
    .filter(([optionId]) => !picked.includes(optionId))
    .map(([, techId]) => techId);
  const allowedKey = allowed.join(",");
  const ownedKey = (me?.techs ?? []).join(",");
  const options = useMemo(
    () => pickTreeOptions(allowedKey ? allowedKey.split(",") : [], ownedKey ? ownedKey.split(",") : []),
    [allowedKey, ownedKey],
  );

  const take = (techId: string) => {
    const optionId = byTech.get(techId);
    if (!optionId) return;
    if (!multi) onChange(optionId);
    else if (input.max === 1) onChange([optionId]);
    else if (picked.length < input.max) onChange([...picked, optionId]);
    setOpen(false);
  };
  const drop = (option: ActionCardOption) =>
    onChange(multi ? picked.filter((id) => id !== option.id) : null);
  const head = multi
    ? pickNote(picked.length, input.min, input.max)
    : pickNote(typeof value === "string" ? 1 : 0, 1, 1);

  return (
    <div className={styles.field}>
      <FieldHead
        label={input.label}
        hint={input.hint}
        note={head.note}
        done={head.done}
      />
      {pickedOptions.length > 0 && (
        <div className={styles.tiles} data-rich>
          {pickedOptions.map((option) => (
            <Tile
              key={option.id}
              option={option}
              kind={{ kind: "technology", target: classified.targets.get(option.id) ?? "" }}
              multi={multi}
              selected
              disabled={disabled}
              onClick={() => drop(option)}
            />
          ))}
        </div>
      )}
      {(room > 0 || !multi) && allowed.length > 0 && (
        <button
          type="button"
          className={styles.treeCall}
          disabled={disabled}
          onClick={() => setOpen(true)}
        >
          {picked.length > 0 && !multi ? "Change in the technology tree" : "Choose in the technology tree"}
        </button>
      )}
      {loose.length > 0 && (
        <div className={styles.tiles}>
          {loose.map((option) => (
            <Tile
              key={option.id}
              option={option}
              multi={multi}
              selected={picked.includes(option.id)}
              disabled={disabled}
              onClick={() =>
                multi
                  ? onChange(
                      picked.includes(option.id)
                        ? picked.filter((id) => id !== option.id)
                        : [...picked, option.id].slice(0, input.max),
                    )
                  : onChange(option.id)
              }
            />
          ))}
        </div>
      )}
      {open && (
        <TechnologyOverlay
          options={options}
          title={input.label}
          subtitle={input.hint || "Pick a highlighted technology."}
          playerRgb={rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "110 168 255"}
          playerName={me?.flexibleDisplayName || me?.faction || ""}
          faction={me?.faction}
          busy={false}
          declineLabel="Close"
          onDecline={() => setOpen(false)}
          onResearch={(payload) => take(payload.tech)}
        />
      )}
    </div>
  );
}
