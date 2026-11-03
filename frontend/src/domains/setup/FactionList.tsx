// Wyniesione (z `pages/StartScreen`) komponenty listy frakcji — jedno źródło
// reużywane przez ekran startowy ORAZ krok `Step_Faction` kreatora setupu.
//
// Zgodnie z design.md (sekcja 8) komponenty `FactionItem` i `QuickReferenceImage`
// zostają wyniesione do `domains/setup/` i reużyte, minimalnie inwazyjnie. Logika
// i wygląd pozostają identyczne jak wcześniej w StartScreen — przenosimy je 1:1,
// a StartScreen importuje je stąd.

import { useState } from "react";
import { Text } from "@/ds";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import type { FactionInfo } from "@/api/useNewGame";
import styles from "./FactionList.module.css";

// Re-eksport modułu stylów — żeby miejsca korzystające z klas listy frakcji
// (np. kontener slotu w StartScreen) miały jedno źródło klas CSS.
export { styles as factionListStyles };

/**
 * Podgląd quick reference frakcji: duży obraz pokazywany na hover/focus.
 * Źródło to Thunder's Edge (TE); gdy plik TE nie istnieje, przełączamy się
 * na PoK przez `onError`. Gdy oba zawiodą — po prostu nie ma obrazu (bez błędu,
 * np. Keleres nie ma pliku quick reference) — R8.3/R8.4: brak obrazu degraduje
 * bez błędu i nie blokuje zatwierdzenia.
 */
export function QuickReferenceImage({ faction }: { faction: FactionInfo }) {
  const te = `/static/quick_reference/TE/${faction.id}.png`;
  const pok = `/static/quick_reference/PoK/${faction.id}.png`;
  // Stan źródła per frakcja: zaczynamy od TE, degradujemy do PoK, potem chowamy.
  const [src, setSrc] = useState(te);
  const [hidden, setHidden] = useState(false);

  if (hidden) {
    return (
      <Text size="xs" c="dimmed" px={4}>
        Brak podglądu quick reference.
      </Text>
    );
  }
  return (
    <img
      src={src}
      alt={`Quick reference: ${faction.name}`}
      className={styles.quickRefImage}
      onError={() => {
        // TE -> PoK, a jeśli i PoK zawiedzie — schowaj bez błędu.
        if (src === te) setSrc(pok);
        else setHidden(true);
      }}
    />
  );
}

/**
 * Pozycja frakcji na liście wyboru. Klik = wybór dla slotu; hover/focus =
 * podgląd quick reference w `SmoothPopover`. Dla „losowej" nie ma podglądu.
 *
 * Opcjonalny `showId` dokleja identyfikator frakcji (`faction.id`) obok nazwy —
 * używany przez krok `Step_Faction` (R8.2: nazwa + identyfikator, bez opisu stylu gry).
 */
export function FactionItem({
  faction,
  active,
  opened,
  showId = false,
  onHover,
  onPick,
}: {
  faction: FactionInfo;
  active: boolean;
  /** Czy to właśnie TEN element ma pokazywać podgląd (stan trzymany w slocie). */
  opened: boolean;
  /** Czy pokazać identyfikator frakcji (`faction.id`) obok nazwy. */
  showId?: boolean;
  /** Zgłasza, która frakcja jest „pod myszą/focusem" (id) albo że żadna (null). */
  onHover: (id: string | null) => void;
  onPick: () => void;
}) {
  return (
    <SmoothPopover
      opened={opened}
      // Gdy sam popover chce się zamknąć (np. klik poza), wyczyść wspólny stan.
      onChange={(next) => {
        if (!next) onHover(null);
      }}
      position="right"
      withArrow
    >
      <SmoothPopover.Target>
        <button
          type="button"
          className={`${styles.factionItem} ${active ? styles.factionItemActive : ""}`}
          aria-pressed={active}
          onClick={onPick}
          onMouseEnter={() => onHover(faction.id)}
          // Opuszczenie SAMEGO elementu też chowa podgląd (jeśli to ten element
          // był otwarty). To trzecia, niezależna ścieżka zamknięcia obok
          // mouseleave listy i scrolla — dzięki niej karta nie „zostaje", gdy
          // kursor wyjdzie poza listę nie przez jej obszar.
          onMouseLeave={() => {
            if (opened) onHover(null);
          }}
          onFocus={() => onHover(faction.id)}
          onBlur={() => onHover(null)}
        >
          <CircularFactionIcon faction={faction.id} size={28} />
          <span className={styles.factionItemLabel}>{faction.name}</span>
          {showId && <span className={styles.factionItemId}>{faction.id}</span>}
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown>
        <div className={styles.quickRefCard}>
          <p className={styles.quickRefName}>{faction.name}</p>
          <QuickReferenceImage faction={faction} />
        </div>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
