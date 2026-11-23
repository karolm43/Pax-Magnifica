import { IconMapPin, IconX } from "@tabler/icons-react";
import { create } from "zustand";
import type { AgendaPhaseData } from "@/entities/data/types";
import { useMapTargets } from "@/domains/strategy/mapPick";
import { MapPickStatus } from "@/domains/offers/MapPickStatus";
import { PHASE_WINDOW } from "@/hooks/useDecisionZone";
import styles from "./AgendaOverlay.module.css";

/*
 * Wybór wyniku agendy „Elect Planet” (U6, decyzja użytkownika: planetę wybiera się WYŁĄCZNIE
 * klikiem na mapie). Okno Rady zasłania planszę, więc na czas wyboru chowa się do paska
 * „kliknij planetę”; podświetlone są tylko planety-wyniki (przy remisie - tylko remisowe).
 * Klik wraca do Rady z wybranym wynikiem; lista wyników na podium to już tylko podgląd głosów.
 */

/** Czy wyniki agendy to planety (wybór na mapie, nie z listy). „planet_trait” to typy planet. */
export function isPlanetAgenda(kind: string): boolean {
  return kind.startsWith("planet") && kind !== "planet_trait";
}

/** Planety, które można teraz wskazać: przy remisie tylko remisowe, inaczej wszystkie wyniki. */
export function pickablePlanets(agenda: AgendaPhaseData): string[] {
  if (agenda.step === "TIEBREAK" && agenda.tied.length > 0) return agenda.tied;
  return agenda.outcomes;
}

type PickState = {
  /** Trwa wybór na mapie (okno Rady schowane). */
  picking: boolean;
  /** Planeta wskazana na mapie - okno Rady odbiera ją po powrocie (``take``). */
  picked: string | null;
  start: () => void;
  finish: (planet: string | null) => void;
  take: () => string | null;
};

export const useAgendaMapPick = create<PickState>((set, get) => ({
  picking: false,
  picked: null,
  start: () => set({ picking: true, picked: null }),
  finish: (planet) => set({ picking: false, picked: planet }),
  take: () => {
    const planet = get().picked;
    if (planet != null) set({ picked: null });
    return planet;
  },
}));

/** Pasek wyboru planety na mapie (w miejscu okna Rady). */
export function AgendaMapPickBar({ agenda }: { agenda: AgendaPhaseData }) {
  const finish = useAgendaMapPick((s) => s.finish);
  const planets = pickablePlanets(agenda);
  const handle = useMapTargets({ planets }, (planet) => finish(planet));
  return (
    // Nadal okno fazy agendy (U3): Decisions czeka jako „+N”, dymki mapy nie wchodzą na pasek.
    <div
      className={styles.mapPickBar}
      role="dialog"
      aria-label="Choose a planet on the map"
      {...PHASE_WINDOW}
    >
      <IconMapPin size={16} aria-hidden="true" />
      <b>{agenda.card?.name ?? "Agenda"}</b>
      <MapPickStatus
        targets={planets.map((id) => ({ kind: "planet" as const, id }))}
        handle={handle}
        disabled={false}
      />
      <button type="button" className={styles.ghostBtn} onClick={() => finish(null)}>
        <IconX size={14} aria-hidden="true" /> Back to the Council
      </button>
    </div>
  );
}
