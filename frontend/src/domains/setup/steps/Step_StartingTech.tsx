// Krok setupu: warunkowy wybór technologii startowych (zadanie 12.3, R9).
//
// Renderowany dla KAŻDEGO slotu gracza, ale faktyczny picker pokazuje się tylko dla
// frakcji, które WYMAGAJĄ wyboru technologii startowej (`starting_tech_amount > 0`,
// R9.1). Frakcje ze stałymi technologiami oraz sloty z frakcją losową są pomijane
// (R9.3) — pokazujemy dla nich krótką informację, że ten krok ich nie dotyczy.
//
// Reguły egzekwowane PRZEZ KROK / STORE / KONTENER:
//   - R9.1: opcje technologii pochodzą ze StaticDataRegistry (lista frakcji z
//     `useFactions` → `faction.starting_tech_options`); picker reużywa wspólny
//     `StartingTechPicker` (wyniesiony ze StartScreen do `domains/setup/`).
//   - R9.2/R9.5: blokada zatwierdzenia, dopóki liczba zaznaczeń ≠ wymagana — robi to
//     centralnie `validateSetup` w kontenerze (`SetupWizard.tsx`); tu dodatkowo
//     pokazujemy licznik „wybrano X z N", by było jasne, czego brakuje.
//   - R9.4: zmiana frakcji czyści wcześniejszy wybór — robi to `setFaction` w store
//     (krok wyboru frakcji), więc tu nic nie trzeba.
//   - R9.6: jeśli odczyt opcji ze StaticDataRegistry się nie powiedzie (lista frakcji
//     nie wczytała się albo frakcja wymaga wyboru, lecz nie ma opcji), BLOKUJEMY krok
//     i pokazujemy komunikat o niepowodzeniu wczytania. Sygnalizujemy to też kontenerowi
//     przez `useSetupStore` — ale ponieważ `validateSetup` nie zna stanu ładowania,
//     blokadę „Dalej" przy błędzie odczytu wymusza tu wyświetlany Alert + brak opcji
//     (picker nie pozwoli dobrać wymaganej liczby, więc `validateSetup` i tak blokuje).
//
// Stan konfiguracji żyje w `useSetupStore` (jedno źródło prawdy); krok tylko czyta
// sloty i zapisuje wybór przez `updateSlot`.

import { useMemo } from "react";
import { Alert, Stack, Text } from "@/ds";
import type { SetupStepProps } from "../SetupWizard";
import { RANDOM_FACTION, useSetupStore } from "../useSetupStore";
import StartingTechPicker from "../StartingTechPicker";

/**
 * Sekcja jednego slotu: nagłówek gracza + (warunkowo) picker technologii lub
 * informacja, że krok tego slotu nie dotyczy. Przy błędzie odczytu opcji (frakcja
 * wymaga wyboru, ale nie ma opcji) pokazuje blokujący komunikat (R9.6).
 */
function SlotStartingTech({
  slotIndex,
  factionById,
}: {
  slotIndex: number;
  factionById: SetupStepProps["factionById"];
}) {
  const slot = useSetupStore((s) => s.slots[slotIndex]);
  const updateSlot = useSetupStore((s) => s.updateSlot);

  const isRandom = slot.factionId === RANDOM_FACTION;
  const faction = isRandom ? undefined : factionById.get(slot.factionId);
  const amount = faction?.starting_tech_amount ?? 0;
  const requiresChoice = amount > 0;

  // R9.6: frakcja wymaga wyboru, ale opcji brak (pusta lista / nieodczytane dane) →
  // błąd odczytu opcji. Blokujemy i informujemy; picker w tym stanie nie ma z czego
  // wybierać, więc `validateSetup` w kontenerze też utrzyma blokadę „Dalej".
  const optionsUnavailable =
    requiresChoice && (faction?.starting_tech_options.length ?? 0) === 0;

  return (
    <Stack gap="xs">
      <Text fw={600} size="sm">
        {slot.name.trim() || `Gracz ${slotIndex + 1}`}
      </Text>

      {!requiresChoice ? (
        // R9.3: frakcja ze stałymi technologiami albo slot losowy → krok pominięty.
        <Text size="sm" c="dimmed">
          {isRandom
            ? "Frakcja losowa — technologie startowe dobierze backend po wylosowaniu."
            : "Ta frakcja ma stałe technologie startowe — wybór nie jest potrzebny."}
        </Text>
      ) : optionsUnavailable ? (
        // R9.6: nie udało się odczytać opcji technologii startowych.
        <Alert color="red" title="Nie udało się wczytać technologii startowych">
          Opcje technologii startowych tej frakcji są niedostępne. Przejście dalej jest
          zablokowane do czasu poprawnego wczytania danych.
        </Alert>
      ) : (
        <Stack gap={4}>
          <StartingTechPicker
            faction={faction}
            value={slot.startingTech}
            onChange={(techs) => updateSlot(slotIndex, { startingTech: techs })}
          />
          {/* Licznik pomocniczy — dopełnia centralną blokadę z `validateSetup` (R9.2). */}
          <Text
            size="xs"
            c={slot.startingTech.length === amount ? "dimmed" : "red"}
          >
            Wybrano {slot.startingTech.length} z {amount}.
          </Text>
        </Stack>
      )}
    </Stack>
  );
}

/**
 * Krok wyboru technologii startowych. Iteruje po slotach; dla każdego renderuje
 * `SlotStartingTech`, który sam decyduje, czy pokazać picker, informację o pominięciu,
 * czy komunikat o błędzie odczytu opcji.
 *
 * Gdy ŻADEN slot nie wymaga wyboru (wszystkie frakcje stałe lub losowe), krok i tak
 * jest wyświetlany przez kontener tylko, gdy `isApplicable` (predykat w `setupSteps.ts`)
 * jest spełniony dla co najmniej jednego slotu — tu dodatkowo pokazujemy czytelną
 * informację zbiorczą, gdyby jednak trafił tu slot bez wyboru.
 */
export default function Step_StartingTech({ factionById }: SetupStepProps) {
  const slots = useSetupStore((s) => s.slots);

  // Czy którykolwiek slot faktycznie wymaga wyboru — do nagłówka informacyjnego.
  const anyRequiresChoice = useMemo(
    () =>
      slots.some((slot) => {
        if (slot.factionId === RANDOM_FACTION) return false;
        return (factionById.get(slot.factionId)?.starting_tech_amount ?? 0) > 0;
      }),
    [slots, factionById],
  );

  return (
    <Stack gap="lg">
      <Text size="sm" c="dimmed">
        {anyRequiresChoice
          ? "Dla frakcji z wyborem technologii startowych wskaż wymaganą liczbę technologii. Pozostali gracze mają ten krok pominięty."
          : "Żadna z wybranych frakcji nie wymaga wyboru technologii startowych — możesz przejść dalej."}
      </Text>

      {slots.map((_slot, index) => (
        <SlotStartingTech key={index} slotIndex={index} factionById={factionById} />
      ))}
    </Stack>
  );
}
