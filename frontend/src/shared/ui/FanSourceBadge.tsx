// Mała plakietka źródła fanowskiej karty (np. „ABS" = Absol) przy nazwie karty.
// Karty oficjalne (base/PoK/codexy/TE) nie dostają plakietki.

import { fanSourceBadge } from "@/entities/data/officialSources";
import styles from "./FanSourceBadge.module.css";

const SOURCE_NAMES: Record<string, string> = {
  absol: "Absol",
};

type Props = {
  /** Pole `source` karty z danych (np. "absol"). */
  source: string | undefined;
  className?: string;
};

export function FanSourceBadge({ source, className }: Props) {
  const label = fanSourceBadge(source);
  if (!label || !source) return null;
  const name = SOURCE_NAMES[source] ?? source;
  return (
    <span
      className={className ? `${styles.badge} ${className}` : styles.badge}
      title={`${name} card (fan-made)`}
      aria-label={`${name} card`}
    >
      {label}
    </span>
  );
}
