import { useState } from "react";
import { useOfferActions, type OfferView } from "@/api/useOffers";
import { TechnologyOverlay } from "@/domains/technology/TechnologyOverlay";
import { toResearchOptions } from "@/domains/technology/techModel";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { useGameData } from "@/state/useGameContext";

/** Klucz wejścia ``research`` (``core/research_offer.RESEARCH_KEY``). */
const RESEARCH_KEY = "research";

/** Czy decyzja to „zbadaj technologię” (pełne okno badania zamiast formularza). */
export function isResearchOffer(offer: OfferView): boolean {
  return offer.inputs.some((input) => input.kind === "research");
}

/**
 * Decyzja badania z komponentu (Focused Research…): TO SAMO pełne okno drzewa technologii co
 * karta strategii Technology, zamiast listy technologii w formularzu. Koszt pokazuje silnik
 * (już po zniżce Doctor Sucaban, użytej przed zapłatą - RULES.md 62.3).
 */
export function ResearchOfferOverlay({ offer }: { offer: OfferView }) {
  const actions = useOfferActions();
  const gameData = useGameData();
  const [busy, setBusy] = useState(false);
  const input = offer.inputs.find((i) => i.kind === "research");
  if (!input || input.kind !== "research") return null;
  const decider = gameData?.playerData?.find((p) => p.discordId === offer.player_id);
  const rgb = decider?.color ? resolvePrimaryRgb(decider.color) : undefined;

  const answer = async (payload: Record<string, unknown>) => {
    setBusy(true);
    try {
      await actions.accept(offer.player_id, offer.id, { [RESEARCH_KEY]: payload });
    } catch {
      // Powód (422) pokazał komunikat; okno zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };

  const options = toResearchOptions(input.research);
  // „Gain” obowiązkowy (Research Grant Reallocation): bez przycisku rezygnacji.
  const canDecline = !options.gain?.mandatory;

  return (
    <TechnologyOverlay
      key={offer.id}
      options={options}
      title={offer.name}
      subtitle={input.hint ? `${input.label} · ${input.hint}` : input.label}
      playerRgb={rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "110 168 255"}
      playerName={decider?.flexibleDisplayName || decider?.faction || ""}
      faction={decider?.faction}
      busy={busy}
      declineLabel={canDecline ? "Don't research" : undefined}
      onDecline={canDecline ? () => void answer({ tech: null }) : undefined}
      onResearch={(payload) => void answer(payload)}
    />
  );
}
