import type { PromptPlayer, StrategyPrompt } from "../strategyPrompt";

/** Wygląd karty (kolor, nazwa, numer) przekazywany widokom do nagłówka okna. */
export type CardShell = { hue: string; initiative: number; title: string };

/** Układ stołu: kolory graczy w kolejności zasiadania (zgodnie z zegarem) i mówca. */
export type TableInfo = { seating: string[]; speaker: string | null };

export type PrimaryViewProps = {
  prompt: StrategyPrompt;
  shell: CardShell;
  owner: PromptPlayer | undefined;
  players: PromptPlayer[];
  table: TableInfo;
  busy: boolean;
  submit: (payload: Record<string, unknown>) => void;
};

export type SecondaryViewProps = {
  prompt: StrategyPrompt;
  shell: CardShell;
  responder: PromptPlayer | undefined;
  players: PromptPlayer[];
  busy: boolean;
  /** Potwierdza „follow" z wyborami. */
  submit: (payload: Record<string, unknown>) => void;
  /** Wraca do decyzji follow / don't follow. */
  back: () => void;
};

/** Nazwa gracza do wyświetlenia (jak w pozostałych oknach). */
export function playerLabel(p: PromptPlayer): string {
  const clean = (v?: string | null) => {
    const t = v?.trim();
    return t && t.toLowerCase() !== "null" ? t : null;
  };
  return (
    clean(p.displayName) ?? clean(p.userName) ?? clean(p.flexibleDisplayName) ?? clean(p.faction) ?? p.color
  );
}
