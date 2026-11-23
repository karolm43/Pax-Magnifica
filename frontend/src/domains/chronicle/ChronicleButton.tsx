import cx from "clsx";
import { IconFeather } from "@tabler/icons-react";
import zoomClasses from "@/shared/ui/map/ZoomControls.module.css";
import { useChronicle, useChronicleUnread } from "./useChronicle";
import { useChronicleStore } from "./useChronicleStore";
import classes from "./ChronicleButton.module.css";

/**
 * Mały przycisk Kroniki Imperium przy przycisku Events. Zachęta do kliknięcia: złoty „oddech”
 * wokół księgi, powolne pisanie pióra i — gdy powstały nowe ważne wydarzenia — błysk oraz
 * licznik. (Animacje wyłącza `prefers-reduced-motion`.)
 */
export function ChronicleButton() {
  const { chapters } = useChronicle();
  const { unread } = useChronicleUnread(chapters);
  const open = useChronicleStore((s) => s.open);
  const setOpen = useChronicleStore((s) => s.setOpen);
  const label = unread > 0 ? `Chronicle of the Empire, ${unread} new` : "Chronicle of the Empire";
  return (
    <button
      type="button"
      className={cx(zoomClasses.zoomButton, classes.button, unread > 0 && classes.fresh)}
      aria-label={label}
      title={label}
      aria-haspopup="dialog"
      aria-expanded={open}
      onClick={() => setOpen(true)}
    >
      <span className={classes.halo} aria-hidden="true" />
      <IconFeather size={15} className={classes.quill} />
      {unread > 0 && <span className={classes.badge}>{unread > 99 ? "99+" : unread}</span>}
    </button>
  );
}
