import { IconWand } from "@tabler/icons-react";
import styles from "./AutoButton.module.css";

/**
 * Jedno „Auto” w całej grze (decyzja użytkownika: każdy wybór = ręcznie + „Auto”). Zawsze przy
 * polu, styl pomocniczy; akcja główna okna (Confirm/Use) zostaje w stopce i jest mocniejsza.
 * `pressed` — gdy wybór równa się podpowiedzi „Auto”.
 */
export function AutoButton({
  onClick,
  disabled,
  pressed,
  title,
  className,
}: {
  onClick: () => void;
  disabled?: boolean;
  pressed?: boolean;
  title?: string;
  /** Dopasowanie rozmiaru do przycisków okna (np. rząd Auto / Clear / Confirm w walce). */
  className?: string;
}) {
  return (
    <button
      type="button"
      className={className ? `${styles.auto} ${className}` : styles.auto}
      disabled={disabled}
      aria-pressed={pressed}
      title={title}
      onClick={onClick}
    >
      <IconWand size={14} aria-hidden="true" /> Auto
    </button>
  );
}
