import { useRef } from "react";
import type { BattleSide } from "@/api/useBoardEditor";
import { expandShips, type ShipEntity } from "./battleAssign";

/**
 * STABILNA TOŻSAMOŚĆ egzemplarzy na polu bitwy (czysta prezentacja).
 *
 * Silnik zna tylko liczby (typ → ile sztuk, ile uszkodzonych). Gdyby id egzemplarza wynikało
 * z indeksu (``cv-0``, ``cv-1``…), po zniszczeniu klikniętego ``cv-0`` znikałby zawsze OSTATNI
 * okręt — gracz widziałby śmierć innej sztuki niż wybrana. Tu każdy egzemplarz zachowuje id
 * między odczytami stanu, a zmiany liczb rozkładamy na egzemplarze wg ZAMIARU gracza
 * (kliknięte do zniszczenia / Sustain), a bez zamiaru — przewidywalnie (od końca szeregu).
 */

/** Co gracz właśnie zlecił (przypisanie strat, wskazanie jednostki) — id egzemplarzy. */
export type ShipIntent = {
  /** Egzemplarze oznaczone do zniszczenia (jako pierwsze znikają). */
  destroy: ReadonlySet<string>;
  /** Egzemplarze oznaczone do Sustain Damage (jako pierwsze stają się uszkodzone). */
  sustain: ReadonlySet<string>;
  /** Wskazane w decyzji (Assault Cannon, naprawa…): pierwsze do każdej zmiany. */
  prefer: ReadonlySet<string>;
  /** Kiedy zlecono (ms, `Date.now()`) — stary zamiar wygasa (`INTENT_TTL_MS`). */
  at?: number;
};

/** Zamiar starszy niż tyle ms nie dotyczy już bieżącej zmiany składu. */
export const INTENT_TTL_MS = 15000;

export const NO_INTENT: ShipIntent = {
  destroy: new Set(),
  sustain: new Set(),
  prefer: new Set(),
};

/** Numer egzemplarza z id ``<baseType>-<n>`` (do nadawania kolejnych, unikalnych id). */
function indexOf(id: string): number {
  const n = Number(id.slice(id.lastIndexOf("-") + 1));
  return Number.isFinite(n) ? n : -1;
}

/**
 * Nowy skład (``fresh`` z ``expandShips``) nałożony na poprzedni (``prev``, stabilne id).
 * Zachowuje kolejność i id ocalałych; znikające/uszkadzane egzemplarze wybiera wg ``intent``.
 */
export function reconcileShips(
  prev: ShipEntity[],
  fresh: ShipEntity[],
  intent: ShipIntent = NO_INTENT,
): ShipEntity[] {
  if (prev.length === 0) return fresh;
  const types = [...new Set([...fresh.map((s) => s.baseType)])];
  const out: ShipEntity[] = [];
  for (const type of types) {
    const want = fresh.filter((s) => s.baseType === type);
    const unit = want[0].unit;
    let kept = prev.filter((s) => s.baseType === type);
    const targetDamaged = want.filter((s) => s.damaged).length;

    // 1. Ubytek: najpierw wskazane do zniszczenia, potem (gdy uszkodzonych jest więcej niż
    //    powinno zostać) uszkodzone, a na końcu — od końca szeregu.
    let remove = kept.length - want.length;
    if (remove > 0) {
      const gone = new Set<string>();
      const take = (pred: (s: ShipEntity) => boolean) => {
        for (const s of [...kept].reverse()) {
          if (remove <= 0) return;
          if (!gone.has(s.id) && pred(s)) {
            gone.add(s.id);
            remove -= 1;
          }
        }
      };
      take((s) => intent.destroy.has(s.id));
      take((s) => intent.prefer.has(s.id));
      const extraDamaged = () =>
        kept.filter((s) => s.damaged && !gone.has(s.id)).length - targetDamaged;
      take((s) => s.damaged && extraDamaged() > 0);
      take(() => true);
      kept = kept.filter((s) => !gone.has(s.id));
    }

    // 2. Przyrost (produkcja, God-Mode): nowe egzemplarze na końcu, z kolejnym wolnym numerem.
    let next = Math.max(-1, ...prev.filter((s) => s.baseType === type).map((s) => indexOf(s.id))) + 1;
    const ships = kept.map((s) => ({ ...s }));
    while (ships.length < want.length) {
      ships.push({ ...want[ships.length], id: `${type}-${next}`, damaged: false });
      next += 1;
    }

    // 3. Uszkodzenia: Sustain trafia we wskazane egzemplarze; naprawa zdejmuje od końca.
    let damaged = ships.filter((s) => s.damaged).length;
    const flip = (pred: (s: ShipEntity) => boolean, to: boolean) => {
      const order = to ? ships : [...ships].reverse();
      for (const s of order) {
        if (damaged === targetDamaged) return;
        if (s.damaged !== to && pred(s)) {
          s.damaged = to;
          damaged += to ? 1 : -1;
        }
      }
    };
    if (damaged < targetDamaged) {
      flip((s) => intent.sustain.has(s.id), true);
      flip((s) => intent.prefer.has(s.id), true);
      flip(() => true, true);
    } else if (damaged > targetDamaged) {
      flip((s) => intent.prefer.has(s.id), false);
      flip(() => true, false);
    }

    // 4. Pola wyliczane jak w ``expandShips`` (Sustain tylko dla ``sustainable`` całych sztuk).
    let whole = 0;
    for (const s of ships) {
      const canSustain = unit.sustain && !s.damaged && whole < unit.sustainable;
      if (!s.damaged) whole += 1;
      out.push({
        ...s, unit, name: unit.name, asyncId: unit.asyncId, canSustain, shield: !!unit.shield,
      });
    }
  }
  return out;
}

/**
 * Hook: egzemplarze strony ze stabilnymi id. ``intent`` czyta się przy KAŻDEJ zmianie składu;
 * zamiar jest zużywany przez pierwszą zmianę, która go dotyczy (``consume``).
 */
export function useStableShips(
  side: BattleSide | null,
  intent: ShipIntent,
  consume: () => void,
): ShipEntity[] {
  const fresh = expandShips(side);
  const signature = fresh.map((s) => `${s.id}:${s.damaged ? 1 : 0}`).join(",");
  const memo = useRef<{ signature: string; ships: ShipEntity[] } | null>(null);
  if (!memo.current) {
    memo.current = { signature, ships: fresh };
  } else if (memo.current.signature !== signature) {
    const touched = [...intent.destroy, ...intent.sustain, ...intent.prefer].length > 0;
    memo.current = { signature, ships: reconcileShips(memo.current.ships, fresh, intent) };
    if (touched) consume();
  } else {
    // Ten sam skład — odśwież tylko dane jednostek (modyfikatory, nazwy) pod stabilnymi id.
    memo.current.ships = memo.current.ships.map((s) => {
      const unit = side?.units.find((u) => u.baseType === s.baseType);
      return unit ? { ...s, unit } : s;
    });
  }
  return memo.current.ships;
}
