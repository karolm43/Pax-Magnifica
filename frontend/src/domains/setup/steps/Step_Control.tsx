// Krok setupu: człowiek / bot + poziom trudności (zadanie 12.4).
//
// Dla KAŻDEGO slotu gracza pokazuje przełącznik typu sterowania (HUMAN/BOT, R10.1).
// Gdy wybrano BOT, pojawia się wybór poziomu trudności z DOZWOLONEGO zbioru (R10.2);
// przy HUMAN pole trudności jest ukryte. Zbiór trudności NIE jest trzymany na froncie
// — pochodzi z backendu (`GET /engine/config` → `valid_difficulties`, czytane przez
// `StaticDataRegistry` z `engine_config.json`), zgodnie z zasadą „zero hardkodowania
// konfiguracji silnika z pamięci".
//
// Komponent jest „cienki": cały stan slotów i reguła czyszczenia trudności przy HUMAN
// (R10.4) żyją w `useSetupStore.ts` (`setControlType`, `updateSlot`). Blokada „Dalej"
// przy BOT bez wybranej trudności jest egzekwowana centralnie przez `validateSetup`
// w kontenerze — tu dodatkowo pokazujemy pole jako „wymagane", gdy puste.

import { Alert, Loader, Select, SegmentedControl, Stack, Text } from "@/ds";
import { useEngineConfig } from "@/api/useNewGame";
import type { SetupStepProps } from "../SetupWizard";
import { useSetupStore, type ControlType } from "../useSetupStore";

/** Dozwolone wartości przełącznika sterowania (R10.1) — odwzorowują `ControlType`. */
const CONTROL_OPTIONS: { label: string; value: ControlType }[] = [
  { label: "Człowiek", value: "HUMAN" },
  { label: "Bot", value: "BOT" },
];

/**
 * Krok „Człowiek / bot": per slot przełącznik HUMAN/BOT i — dla botów — wybór
 * poziomu trudności z zbioru pobranego z backendu. Propsy `SetupStepProps` nie są
 * tu potrzebne (lista frakcji nie dotyczy tego kroku), ale zachowujemy sygnaturę
 * zgodną z rejestrem kroków w kontenerze.
 */
export default function StepControl(_props: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);
  const setControlType = useSetupStore((s) => s.setControlType);
  const updateSlot = useSetupStore((s) => s.updateSlot);

  // Dozwolony zbiór trudności z backendu (jedno źródło prawdy — bez kopii na froncie).
  const { data: engineConfig, isLoading, isError } = useEngineConfig();
  const difficulties = engineConfig?.valid_difficulties ?? [];

  return (
    <Stack gap="lg">
      <Text size="sm" c="dimmed">
        Ustaw, czy danym graczem steruje człowiek, czy bot. Dla bota wybierz poziom
        trudności z dozwolonego zbioru.
      </Text>

      {slots.map((slot, index) => {
        const isBot = slot.controlType === "BOT";
        // Dla bota trudność musi być wybrana (R10.2); puste pole oznaczamy jako błąd,
        // co spina się z blokadą „Dalej" w kontenerze (`validateSetup`).
        const difficultyError =
          isBot && !slot.difficulty ? "Wybierz poziom trudności bota." : undefined;

        return (
          <Stack key={index} gap="xs">
            <Text fw={600} size="sm">
              {slot.name.trim() || `Gracz ${index + 1}`}
            </Text>

            {/* Przełącznik typu sterowania — zmiana na HUMAN czyści trudność (R10.4). */}
            <SegmentedControl
              aria-label={`Typ sterowania gracza ${index + 1}`}
              data={CONTROL_OPTIONS}
              value={slot.controlType}
              onChange={(value) => setControlType(index, value as ControlType)}
            />

            {/* Wybór trudności tylko dla bota (przy HUMAN ukryty — R10.2). */}
            {isBot &&
              (isLoading ? (
                <Loader size="sm" />
              ) : isError ? (
                <Alert color="red" title="Nie udało się pobrać poziomów trudności">
                  Spróbuj ponownie — bez dozwolonego zbioru nie można ustawić bota.
                </Alert>
              ) : (
                <Select
                  aria-label={`Poziom trudności bota gracza ${index + 1}`}
                  label="Poziom trudności"
                  placeholder="Wybierz poziom"
                  data={difficulties}
                  value={slot.difficulty}
                  onChange={(value) =>
                    updateSlot(index, { difficulty: value ?? null })
                  }
                  error={difficultyError}
                  required
                />
              ))}
          </Stack>
        );
      })}
    </Stack>
  );
}
