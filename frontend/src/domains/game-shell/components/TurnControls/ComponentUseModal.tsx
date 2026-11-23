import { useMemo, useState, type ReactNode } from "react";
import { Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { DecisionFrame } from "@/shared/ui/DecisionFrame";
import type { ComponentRef } from "@/domains/cards/components/ComponentInfo";
import { DecisionFields } from "@/domains/offers/DecisionFields";
import {
  buildActionCardParams,
  hasNoLegalOption,
  type ActionCardInput,
  type FormValue,
} from "@/api/useActionCard";

type Props = {
  /** Nazwa komponentu (tytuł ramy) albo gotowy chip (np. `Tech`). */
  title: ReactNode;
  /** Plakietka rodzaju: „Action card”, „Technology”, „Leader”... */
  kind: string;
  infoRef?: ComponentRef;
  infoName?: string;
  loading: boolean;
  /** Komunikat błędu ładowania formularza (`null` = brak). */
  error: string | null;
  /** Pełny tekst komponentu z danych; `undefined` do czasu załadowania formularza. */
  text?: string;
  /** Dopisek pod tekstem, pogrubiony (np. podsumowanie karty). */
  summary?: string;
  /** Neutralne komunikaty (koszt akcji, brak automatu, HOLD) i ostrzeżenia (wyczerpane). */
  notes?: string[];
  warnings?: string[];
  inputs: ActionCardInput[];
  /** Czy pokazać pola (np. nie dla zablokowanego lidera). */
  showForm?: boolean;
  /** Wyczerpane / zablokowane: akcja główna nieaktywna. */
  blocked?: boolean;
  /** Komunikat, gdy formularz nie ma żadnej legalnej opcji. */
  noOptionsMessage?: string;
  /** Etykieta akcji głównej; brak = tylko zamknięcie. */
  useLabel?: string;
  /** Wykonanie akcji; po sukcesie wywołujący zamyka okno. Błąd (422) zostawia okno otwarte. */
  onUse?: (params: Record<string, unknown>) => Promise<void>;
  cancelLabel?: string;
  onClose: () => void;
  /** Dodatkowa akcja w stopce (np. ręczne odblokowanie lidera). */
  secondary?: { label: string; run: () => Promise<void> };
  size?: number;
};

/**
 * Jedno okno „użyj komponentu” (karta akcji / relikt / notka / technologia / lider / legendarna
 * planeta) — zamiast czterech osobnych modali. Treść w `DecisionFrame` (chip + ⓘ, pełny tekst,
 * pola `DecisionFields`, Cancel Esc / Use Enter). Formularz opisuje backend; wywołujący podaje
 * tylko, co wysłać (`onUse`).
 */
export function ComponentUseModal({
  title,
  kind,
  infoRef,
  infoName,
  loading,
  error,
  text,
  summary,
  notes = [],
  warnings = [],
  inputs,
  showForm = true,
  blocked = false,
  noOptionsMessage = "There is nothing to use it on right now.",
  useLabel,
  onUse,
  cancelLabel = "Cancel",
  onClose,
  secondary,
  size = 480,
}: Props) {
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [busy, setBusy] = useState(false);
  const { params, ready } = useMemo(() => buildActionCardParams(inputs, values), [inputs, values]);
  const noOptions = showForm && hasNoLegalOption(inputs);
  const loaded = text !== undefined;

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód pokazał już komunikat; okno zostaje do poprawki wyboru.
    } finally {
      setBusy(false);
    }
  };

  const allNotes = summary ? [summary, ...notes] : notes;
  const allWarnings = [...(error ? [error] : []), ...(noOptions && !blocked ? [noOptionsMessage] : []), ...warnings];
  const ariaName = typeof title === "string" ? title : (infoName ?? kind);

  return (
    <AppModal
      floating
      opened
      onClose={onClose}
      withCloseButton={false}
      size={size}
      title={undefined}
    >
      {loading && (
        <Text size="sm" c="dimmed">
          Loading…
        </Text>
      )}
      {!loading && (
        <DecisionFrame
          embedded
          ariaLabel={`${kind}: ${ariaName}`}
          kind={kind}
          title={title}
          infoRef={infoRef}
          infoName={infoName}
          text={text}
          notes={allNotes}
          warnings={allWarnings}
          busy={busy}
          canUse={loaded && ready && !noOptions && !blocked}
          onUse={onUse ? () => void run(() => onUse(params)) : undefined}
          useLabel={useLabel}
          onSkip={onClose}
          skipLabel={cancelLabel}
          secondary={secondary && { label: secondary.label, onClick: () => void run(secondary.run) }}
        >
          {loaded && showForm && !blocked && (
            <DecisionFields
              inputs={inputs}
              values={values}
              disabled={busy}
              onChange={(key, next) => setValues((prev) => ({ ...prev, [key]: next }))}
            />
          )}
        </DecisionFrame>
      )}
    </AppModal>
  );
}

/** Komunikat błędu z zapytania formularza. */
export function formError(error: unknown, fallback: string): string | null {
  if (!error) return null;
  return error instanceof Error ? error.message : fallback;
}
