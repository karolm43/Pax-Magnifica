import { useState } from "react";
import {
  IconArrowLeft,
  IconBuildingFactory2,
  IconCheck,
  IconHammer,
  IconTarget,
} from "@tabler/icons-react";
import { useMapPick } from "../mapPick";
import { Button } from "@/ds";
import { getPlanetData } from "@/entities/lookup/planets";
import { ConfirmButton, Hint, PromptShell, Section } from "../PromptParts";
import styles from "../StrategyPrompt.module.css";
import type { StrategyPrompt } from "../strategyPrompt";
import type { CardShell, PrimaryViewProps, SecondaryViewProps } from "./types";

/*
 * Construction, wersja Thunder's Edge (RULES.md 30.12): primary - struktura ALBO PRODUCTION
 * jednego doku, potem druga struktura; secondary - jedna struktura. "Struktura" = PDS lub
 * dok. Backend podaje legalne miejsca (`placeable`: planeta -> struktury).
 */

const STRUCTURE_LABEL: Record<string, string> = { pds: "PDS", spacedock: "Space dock" };

type Dock = { planet: string; position: string; value: number };

function docksOf(prompt: StrategyPrompt): Dock[] {
  const raw = prompt.options.docks;
  return Array.isArray(raw) ? (raw as Dock[]) : [];
}

function placeableOf(prompt: StrategyPrompt): Record<string, string[]> {
  const raw = prompt.options.placeable;
  return raw && typeof raw === "object" ? (raw as Record<string, string[]>) : {};
}

/** Struktura -> planety, z których trzeba ją zdjąć (pusta rezerwa, R_component_limitations). */
function boardSourcesOf(prompt: StrategyPrompt): Record<string, string[]> {
  const raw = prompt.options.board_sources;
  return raw && typeof raw === "object" ? (raw as Record<string, string[]>) : {};
}

type Pick = { planet: string; structure: string; source?: string };

/** Wybór gotowy do wysłania: przy pustej rezerwie musi też mieć planetę źródłową. */
function pickReady(pick: Pick | null, sources: Record<string, string[]>): boolean {
  return pick != null && (!sources[pick.structure] || pick.source != null);
}

/**
 * Wybór planety NA MAPIE (podświetlone legalne planety) i rodzaju struktury w doku.
 * Gdy rezerwa tej struktury jest pusta, drugi klik NA MAPIE wskazuje planetę, z której
 * gracz ją zdejmuje (system bez jego żetonu dowodzenia). Wspólny dla primary i secondary.
 */
function StructurePicker({
  placeable,
  boardSources,
  value,
  onChange,
  busy,
  hue,
}: {
  placeable: Record<string, string[]>;
  boardSources: Record<string, string[]>;
  value: Pick | null;
  onChange: (next: Pick | null) => void;
  busy: boolean;
  hue: string;
}) {
  const planets = Object.keys(placeable);
  const sources = value
    ? (boardSources[value.structure] ?? []).filter((p) => p !== value.planet)
    : [];
  const pickingSource = value != null && sources.length > 0;
  useMapPick(
    "planet",
    pickingSource ? sources : planets,
    (id) => {
      // Ponowny klik w wybrane miejsce odznacza je (jak w każdym wyborze na mapie).
      if (pickingSource && value) onChange({ ...value, source: value.source === id ? undefined : id });
      else if (value?.planet === id) onChange(null);
      else onChange({ planet: id, structure: placeable[id]?.[0] ?? "pds" });
    },
    {
      hue,
      selected: (pickingSource ? value?.source : value?.planet) ?? null,
      enabled: !busy,
    },
  );
  if (planets.length === 0) {
    return <span className={styles.empty}>You have no legal place for a structure.</span>;
  }
  if (value == null) {
    return (
      <Hint>
        <IconTarget size={14} aria-hidden="true" /> <b>Click a highlighted planet</b> on the map
        to place the structure there.
      </Hint>
    );
  }
  return (
    <Section title={`Structure on ${getPlanetData(value.planet)?.name ?? value.planet}`}>
      <div className={styles.chips}>
        {(placeable[value.planet] ?? []).map((s) => (
          <button
            key={s}
            type="button"
            className={styles.chip}
            data-on={value.structure === s || undefined}
            disabled={busy}
            onClick={() => onChange({ planet: value.planet, structure: s })}
          >
            {STRUCTURE_LABEL[s] ?? s}
          </button>
        ))}
      </div>
      {pickingSource ? (
        <>
          <Hint>
            <IconTarget size={14} aria-hidden="true" /> No {STRUCTURE_LABEL[value.structure] ?? value.structure}{" "}
            left in your reinforcements - <b>click a highlighted planet</b> to move one from there
            (a system without your command token).
            {value.source != null && (
              <>
                {" "}Moving from <b>{getPlanetData(value.source)?.name ?? value.source}</b>.
              </>
            )}
          </Hint>
          <Button variant="default" size="xs" disabled={busy} onClick={() => onChange(null)}>
            Change planet
          </Button>
        </>
      ) : (
        <Hint>Click another highlighted planet to change it.</Hint>
      )}
    </Section>
  );
}

function shellProps(shell: CardShell, badge: string, subtitle: string) {
  return { hue: shell.hue, initiative: shell.initiative, title: shell.title, badge, subtitle };
}

export function ConstructionPrimary({ prompt, shell, busy, submit }: PrimaryViewProps) {
  const [pick, setPick] = useState<Pick | null>(null);
  const [dock, setDock] = useState<string | null>(null);
  const step = prompt.step;

  if (step === "choose_option") {
    const hasDocks = docksOf(prompt).length > 0;
    return (
      <PromptShell {...shellProps(shell, "Primary", "Choose one")}>
        <Hint>
          Either <b>place 1 structure</b> on a planet you control, or use the{" "}
          <b>PRODUCTION</b> ability of 1 of your space docks. Then you place 1 more structure.
        </Hint>
        <div className={styles.chips}>
          <button
            type="button"
            className={styles.chip}
            disabled={busy}
            onClick={() => submit({ option: "structure" })}
          >
            <IconHammer size={16} aria-hidden="true" /> Place a structure
          </button>
          <button
            type="button"
            className={styles.chip}
            disabled={busy || !hasDocks}
            title={hasDocks ? undefined : "You have no space dock"}
            onClick={() => submit({ option: "production" })}
          >
            <IconBuildingFactory2 size={16} aria-hidden="true" /> Use a dock's PRODUCTION
          </button>
        </div>
      </PromptShell>
    );
  }

  if (step === "choose_dock") {
    const docks = docksOf(prompt);
    return (
      <PromptShell
        {...shellProps(shell, "Primary", "Choose a space dock")}
        footer={
          <ConfirmButton
            disabled={busy || dock == null}
            icon={<IconCheck size={16} />}
            onClick={() => submit({ planet: dock })}
          >
            Open production
          </ConfirmButton>
        }
      >
        <Hint>
          Only the PRODUCTION of <b>this one dock</b> counts. After producing, press{" "}
          <b>Finish production</b> to place your second structure.
        </Hint>
        <Section title="Your space docks">
          <div className={styles.chips}>
            {docks.map((d) => (
              <button
                key={d.planet}
                type="button"
                className={styles.chip}
                data-on={dock === d.planet || undefined}
                disabled={busy}
                onClick={() => setDock(d.planet)}
              >
                {getPlanetData(d.planet)?.name ?? d.planet}
                <small>PRODUCTION {d.value}</small>
              </button>
            ))}
          </div>
        </Section>
      </PromptShell>
    );
  }

  // place_structure / place_structure_2
  const placeable = placeableOf(prompt);
  const boardSources = boardSourcesOf(prompt);
  const none = Object.keys(placeable).length === 0;
  const second = step === "place_structure_2";
  return (
    <PromptShell
      {...shellProps(shell, "Primary", second ? "Place your second structure" : "Place a structure")}
      footer={
        <ConfirmButton
          disabled={busy || (!none && !pickReady(pick, boardSources))}
          icon={<IconCheck size={16} />}
          onClick={() => submit(none ? { planet: null } : { ...pick })}
        >
          {none ? "Continue (no legal place)" : "Place structure"}
        </ConfirmButton>
      }
    >
      <Hint>
        Place <b>1 structure</b> (PDS or space dock) on a planet you control. Limits: 1 space
        dock and 2 PDS per planet, none on the Demilitarized Zone.
      </Hint>
      <StructurePicker
        placeable={placeable}
        boardSources={boardSources}
        value={pick}
        onChange={setPick}
        busy={busy}
        hue={shell.hue}
      />
    </PromptShell>
  );
}

export function ConstructionSecondary({ prompt, shell, busy, submit, back }: SecondaryViewProps) {
  const [pick, setPick] = useState<Pick | null>(null);
  const boardSources = boardSourcesOf(prompt);
  return (
    <PromptShell
      {...shellProps(shell, "Secondary", "Place a structure")}
      footer={
        <>
          <Button variant="default" disabled={busy} leftSection={<IconArrowLeft size={16} />} onClick={back}>
            Back
          </Button>
          <ConfirmButton
            disabled={busy || !pickReady(pick, boardSources)}
            icon={<IconCheck size={16} />}
            onClick={() => submit({ ...pick })}
          >
            Follow
          </ConfirmButton>
        </>
      }
    >
      <Hint>
        Spend <b>1 token from your strategy pool</b> to place 1 structure on a planet you
        control.
      </Hint>
      <StructurePicker
        placeable={placeableOf(prompt)}
        boardSources={boardSources}
        value={pick}
        onChange={setPick}
        busy={busy}
        hue={shell.hue}
      />
    </PromptShell>
  );
}
