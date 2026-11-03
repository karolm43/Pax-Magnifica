// Krok setupu: nazwa wyświetlana + kolor per gracz (Step_NameColor).
//
// Odpowiedzialności (zadanie 12.1, R7.1/R7.2/R7.4/R7.5/R7.6/R7.8):
//  1. Renderuje — dla każdego slotu gracza — pole nazwy oraz wybór koloru ze zbioru
//     `AVAILABLE_COLORS`.
//  2. Zapisuje zmiany WYŁĄCZNIE do store'a (`updateSlot`), więc dane są zachowane przy
//     przełączaniu kroków (store jest jednym źródłem prawdy konfiguracji).
//  3. Pokazuje lokalne podpowiedzi walidacji per slot (długość nazwy, duplikat nazwy,
//     duplikat koloru). Twarde blokowanie „Dalej" robi kontener przez `validateSetup`
//     ze store'a — tu dajemy tylko czytelny sygnał przy konkretnym slocie.
//
// Komponent jest „cienki": nie trzyma własnego stanu konfiguracji ani nie duplikuje
// reguł walidacji z `useSetupStore.ts` — czyta sloty i woła akcje store'a.

import { Group, Paper, SimpleGrid, Stack, Text, TextInput, UnstyledButton } from "@/ds";
import type { SetupStepProps } from "../SetupWizard";
import {
  AVAILABLE_COLORS,
  MAX_NAME_LENGTH,
  type PlayerColor,
  type SetupSlot,
  useSetupStore,
} from "../useSetupStore";

/** Mapa nazw kolorów (id ze zbioru) na kod CSS dla próbek — tylko prezentacja. */
const COLOR_SWATCH: Record<PlayerColor, string> = {
  red: "#d94a4a",
  green: "#49a14a",
  white: "#e8e8e8",
  blue: "#4a7fd9",
  purple: "#9a4ad9",
  yellow: "#e0c23a",
};

/**
 * Wyznacza lokalny komunikat walidacji dla pojedynczego slotu (albo `null`).
 *
 * Reguły odwzorowują `validateSetup` ze store'a, ale tu zwracamy je per slot, by umieścić
 * podpowiedź przy właściwym polu. Źródłem prawdy do blokady „Dalej" pozostaje store.
 */
function slotNameError(slot: SetupSlot, index: number, slots: SetupSlot[]): string | null {
  const name = slot.name.trim();
  if (name.length > MAX_NAME_LENGTH) {
    return `Najwyżej ${MAX_NAME_LENGTH} znaków.`;
  }
  if (name.length === 0) return null; // pusta nazwa jest OK — backend nada automatyczną
  // Duplikat niepustej nazwy (case-insensitive) z WCZEŚNIEJSZYM slotem — R7.5.
  const normalized = name.toLowerCase();
  for (let i = 0; i < index; i++) {
    if (slots[i].name.trim().toLowerCase() === normalized) {
      return `Nazwa „${name}" jest już użyta przez Gracza ${i + 1}.`;
    }
  }
  return null;
}

/** Czy kolor slotu koliduje z kolorem WCZEŚNIEJSZEGO slotu (duplikat) — R7.8. */
function isColorDuplicate(slot: SetupSlot, index: number, slots: SetupSlot[]): boolean {
  for (let i = 0; i < index; i++) {
    if (slots[i].color === slot.color) return true;
  }
  return false;
}

/** Pojedynczy wiersz slotu gracza: numer + pole nazwy + próbki kolorów. */
function SlotRow({
  slot,
  index,
  slots,
}: {
  slot: SetupSlot;
  index: number;
  slots: SetupSlot[];
}) {
  const updateSlot = useSetupStore((s) => s.updateSlot);
  const nameError = slotNameError(slot, index, slots);
  const colorDuplicate = isColorDuplicate(slot, index, slots);

  return (
    <Paper radius="md" withBorder p="md">
      <Stack gap="sm">
        <Text fw={600} size="sm">
          Gracz {index + 1}
        </Text>

        {/* Nazwa wyświetlana — zapis wprost do store'a (dane zachowane między krokami). */}
        <TextInput
          label="Nazwa"
          placeholder="(puste → nazwa automatyczna)"
          value={slot.name}
          maxLength={MAX_NAME_LENGTH}
          onChange={(e) => updateSlot(index, { name: e.currentTarget.value })}
          error={nameError ?? undefined}
        />

        {/* Wybór koloru ze zbioru AVAILABLE_COLORS — próbki jako przyciski radio. */}
        <Stack gap={4}>
          <Text size="sm" fw={500}>
            Kolor
          </Text>
          <Group gap="xs" role="radiogroup" aria-label={`Kolor gracza ${index + 1}`}>
            {AVAILABLE_COLORS.map((color) => {
              const selected = slot.color === color;
              return (
                <UnstyledButton
                  key={color}
                  role="radio"
                  aria-checked={selected}
                  aria-label={color}
                  onClick={() => updateSlot(index, { color })}
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: COLOR_SWATCH[color],
                    border: selected
                      ? "3px solid var(--ds-color-text, #fff)"
                      : "2px solid rgba(255,255,255,0.25)",
                    boxShadow: selected ? "0 0 0 2px rgba(0,0,0,0.4)" : "none",
                    cursor: "pointer",
                  }}
                />
              );
            })}
          </Group>
          {colorDuplicate ? (
            <Text c="red" size="xs">
              Ten kolor jest już użyty przez innego gracza.
            </Text>
          ) : null}
        </Stack>
      </Stack>
    </Paper>
  );
}

/**
 * Krok „Nazwa i kolor". Lista slotów graczy — każdy z polem nazwy i wyborem korloru.
 * Walidacja (długość, duplikaty) żyje w store'ie; tu renderujemy pola i lokalne
 * podpowiedzi, a kontener blokuje „Dalej" na podstawie `validateSetup`.
 */
export default function Step_NameColor(_props: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);

  return (
    <Stack gap="md">
      <Text size="sm" c="dimmed">
        Nadaj nazwę i kolor każdemu graczowi. Puste pole nazwy zostanie uzupełnione
        automatycznie. Kolory i nazwy muszą być unikalne.
      </Text>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {slots.map((slot, index) => (
          <SlotRow key={index} slot={slot} index={index} slots={slots} />
        ))}
      </SimpleGrid>
    </Stack>
  );
}
