import { useState } from "react";
import { IconArrowLeft, IconBuildingFactory2, IconCheck, IconHammer } from "@tabler/icons-react";
import { Button } from "@/ds";
import { getPlanetData } from "@/entities/lookup/planets";
import { PlanetCard } from "@/domains/player/components/PlanetCard";
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

/** Wybór planety i struktury do położenia (wspólny dla obu kroków primary i secondary). */
function StructurePicker({
  placeable,
  value,
  onChange,
  busy,
}: {
  placeable: Record<string, string[]>;
  value: { planet: string; structure: string } | null;
  onChange: (next: { planet: string; structure: string } | null) => void;
  busy: boolean;
}) {
  const planets = Object.keys(placeable);
  if (planets.length === 0) {
    return <span className={styles.empty}>You have no legal place for a structure.</span>;
  }
  return (
    <Section title="Planet and structure">
      <div className={styles.planets}>
        {planets.map((id) => {
          const picked = value?.planet === id;
          return (
            <div className={styles.planetSlot} key={id}>
              <PlanetCard
                planetId={id}
                picked={picked}
                onPick={busy ? undefined : () => onChange(picked ? null : { planet: id, structure: placeable[id][0] })}
              />
              {picked ? (
                <div className={styles.chips}>
                  {placeable[id].map((s) => (
                    <button
                      key={s}
                      type="button"
                      className={styles.chip}
                      data-on={value?.structure === s || undefined}
                      disabled={busy}
                      onClick={() => onChange({ planet: id, structure: s })}
                    >
                      {STRUCTURE_LABEL[s] ?? s}
                    </button>
                  ))}
                </div>
              ) : (
                <span className={styles.planetValue}>
                  {getPlanetData(id)?.name ?? id}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </Section>
  );
}

function shellProps(shell: CardShell, badge: string, subtitle: string) {
  return { hue: shell.hue, initiative: shell.initiative, title: shell.title, badge, subtitle };
}

export function ConstructionPrimary({ prompt, shell, busy, submit }: PrimaryViewProps) {
  const [pick, setPick] = useState<{ planet: string; structure: string } | null>(null);
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
  const none = Object.keys(placeable).length === 0;
  const second = step === "place_structure_2";
  return (
    <PromptShell
      {...shellProps(shell, "Primary", second ? "Place your second structure" : "Place a structure")}
      footer={
        <ConfirmButton
          disabled={busy || (!none && pick == null)}
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
      <StructurePicker placeable={placeable} value={pick} onChange={setPick} busy={busy} />
    </PromptShell>
  );
}

export function ConstructionSecondary({ prompt, shell, busy, submit, back }: SecondaryViewProps) {
  const [pick, setPick] = useState<{ planet: string; structure: string } | null>(null);
  return (
    <PromptShell
      {...shellProps(shell, "Secondary", "Place a structure")}
      footer={
        <>
          <Button variant="default" disabled={busy} leftSection={<IconArrowLeft size={16} />} onClick={back}>
            Back
          </Button>
          <ConfirmButton
            disabled={busy || pick == null}
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
      <StructurePicker placeable={placeableOf(prompt)} value={pick} onChange={setPick} busy={busy} />
    </PromptShell>
  );
}
