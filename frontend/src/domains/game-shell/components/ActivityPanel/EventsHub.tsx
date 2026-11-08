import { useState } from "react";
import { HistoryPanel } from "../HistoryPanel";
import { ActivityPanel } from "./ActivityPanel";
import classes from "./EventsHub.module.css";

type Tab = "activity" | "snapshots";

const TABS: { key: Tab; label: string }[] = [
  { key: "activity", label: "Activity" },
  { key: "snapshots", label: "Snapshots" },
];

/**
 * Zawartość panelu „History / Events": feed aktywności graczy (domyślnie) oraz
 * migawki stanu do cofania. Feed odpowiada na „co zrobili inni", migawki na
 * „wróć do tego momentu".
 */
export function EventsHub() {
  const [tab, setTab] = useState<Tab>("activity");
  return (
    <div className={classes.root}>
      <div className={classes.tabs} role="tablist" aria-label="History views">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            className={classes.tab}
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className={classes.content} role="tabpanel">
        {tab === "activity" ? (
          <ActivityPanel />
        ) : (
          <div className={classes.snapshots}>
            <HistoryPanel />
          </div>
        )}
      </div>
    </div>
  );
}
