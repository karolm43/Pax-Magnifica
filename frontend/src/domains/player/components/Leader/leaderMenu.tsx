import { IconFlame, IconLockOpen, IconLock } from "@tabler/icons-react";
import type { ContextMenuItem } from "@/shared/ui/ContextMenu/ContextMenu";

/**
 * Pozycje menu kontekstowego lidera (prawy przycisk myszy). Stan lidera w TI4:
 * zablokowany (locked) → gotowy (unlocked/ready) → wyczerpany (exhausted). Menu
 * daje przejścia zależne od bieżącego stanu. Rozszerzalne — dokładaj pozycje do
 * zwracanej tablicy. ``setLeaderState`` z ``useBoardEditor``.
 */
export function leaderContextMenuItems(
  playerId: string,
  leaderId: string,
  exhausted: boolean,
  locked: boolean,
  setLeaderState: (
    playerId: string,
    leaderId: string,
    state: string,
  ) => Promise<void>,
): ContextMenuItem[] {
  const set = (state: string) => () =>
    void setLeaderState(playerId, leaderId, state);

  if (locked) {
    return [
      {
        label: "Odblokuj (unlock)",
        icon: <IconLockOpen size={14} />,
        onSelect: set("unlocked"),
      },
    ];
  }
  if (exhausted) {
    return [
      {
        label: "Refresh (ready)",
        icon: <IconFlame size={14} />,
        onSelect: set("unlocked"),
      },
      {
        label: "Zablokuj (lock)",
        icon: <IconLock size={14} />,
        onSelect: set("locked"),
      },
    ];
  }
  return [
    {
      label: "Wyczerp (exhaust)",
      icon: <IconFlame size={14} />,
      onSelect: set("exhausted"),
    },
    {
      label: "Zablokuj (lock)",
      icon: <IconLock size={14} />,
      onSelect: set("locked"),
    },
  ];
}
