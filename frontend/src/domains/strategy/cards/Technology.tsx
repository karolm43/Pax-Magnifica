import { TechnologyOverlay } from "@/domains/technology/TechnologyOverlay";
import { toResearchOptions } from "@/domains/technology/techModel";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { playerName } from "../PlayerChip";
import type { PromptPlayer } from "../strategyPrompt";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/*
 * Technology (RULES.md 49.2): primary - 1 technologia za darmo, potem opcjonalnie druga za
 * 6 zasobów; secondary - 1 technologia za żeton ze strategy pool i 4 zasoby. Cały wybór
 * odbywa się w pełnoekranowym oknie drzewa technologii (TechnologyOverlay).
 */

function rgbOf(player: PromptPlayer | undefined): string {
  const rgb = player?.color ? resolvePrimaryRgb(player.color) : undefined;
  return rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "110 168 255";
}

export function TechnologyPrimary({ prompt, owner, busy, submit }: PrimaryViewProps) {
  const options = toResearchOptions(prompt.options);
  const second = prompt.step === "research_paid";
  return (
    <TechnologyOverlay
      key={prompt.step ?? "primary"}
      options={options}
      title="Technology"
      subtitle={
        second
          ? "Primary · research a second technology for 6 resources (optional)"
          : "Primary · research 1 technology for free"
      }
      playerRgb={rgbOf(owner)}
      playerName={owner ? playerName(owner) : ""}
      faction={owner?.faction}
      busy={busy}
      declineLabel={second ? "Finish without a second" : "Don't research"}
      onDecline={() => submit({ tech: null })}
      onResearch={(payload) => submit(payload)}
    />
  );
}

export function TechnologySecondary({ prompt, responder, busy, submit, back }: SecondaryViewProps) {
  return (
    <TechnologyOverlay
      options={toResearchOptions(prompt.options)}
      title="Technology"
      subtitle="Secondary · 1 strategy token + 4 resources"
      playerRgb={rgbOf(responder)}
      playerName={responder ? playerName(responder) : ""}
      faction={responder?.faction}
      busy={busy}
      onBack={back}
      onResearch={(payload) => submit(payload)}
    />
  );
}
