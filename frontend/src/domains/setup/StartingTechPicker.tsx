// Współdzielony picker technologii startowych (reużywany w setupie).
//
// Wyniesiony ze `StartScreen.tsx` do `domains/setup/`, analogicznie do `FactionList`,
// żeby mógł go reużyć zarówno stary ekran startowy, jak i krok kreatora
// (`Step_StartingTech.tsx`, zadanie 12.3). Zachowanie i wygląd bez zmian względem
// oryginału — jedyna różnica to lokalizacja i jawny kontrakt propsów.
//
// Komponent pokazuje się TYLKO gdy frakcja wymaga wyboru (`starting_tech_amount > 0`,
// R9.1); dla frakcji ze stałymi technologiami zwraca `null` (krok pomijany — R9.3).
// Ogranicza liczbę zaznaczeń do wymaganej (bierze ostatnie `amount` zaznaczeń).

import { MultiSelect } from "@/ds";
import { getTechData } from "@/entities/lookup/tech";
import type { FactionInfo } from "@/api/useNewGame";

export interface StartingTechPickerProps {
  /** Frakcja slotu (lub `undefined` dla losowej/niewybranej). */
  faction: FactionInfo | undefined;
  /** Aktualnie zaznaczone technologie (aliasy). */
  value: string[];
  /** Wywoływane przy zmianie zaznaczenia (już ograniczone do `amount`). */
  onChange: (techs: string[]) => void;
}

/**
 * Menu wyboru technologii startowej dla frakcji, która NIE ma stałych technologii
 * (np. Winnu wybiera 1 z 8, Argent 2 z 3). Pokazuje się tylko gdy
 * `starting_tech_amount > 0`. Ogranicza wybór do wymaganej liczby.
 */
export default function StartingTechPicker({
  faction,
  value,
  onChange,
}: StartingTechPickerProps) {
  if (!faction || faction.starting_tech_amount <= 0) return null;
  const amount = faction.starting_tech_amount;
  const options = faction.starting_tech_options.map((alias) => ({
    value: alias,
    label: getTechData(alias)?.name ?? alias,
  }));
  return (
    <MultiSelect
      label={`Technologie startowe (wybierz ${amount})`}
      placeholder={`Wybierz ${amount}`}
      data={options}
      value={value}
      onChange={(next) => {
        // Nie pozwól wybrać więcej niż wymaga frakcja (bierzemy ostatnie `amount`).
        onChange(next.length > amount ? next.slice(next.length - amount) : next);
      }}
    />
  );
}
