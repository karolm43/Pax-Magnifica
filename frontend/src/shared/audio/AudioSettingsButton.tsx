/**
 * Przycisk dźwięku w pływającym pasku mapy (obok Events): panel `AudioSettingsPanel` w popoverze.
 * Wygląd przycisku = `zoomButton` (jak sąsiednie), panel = `Popover` z design systemu.
 */
import { useState } from "react";
import cx from "clsx";
import { IconVolume, IconVolumeOff } from "@tabler/icons-react";
import { Popover } from "@/ds";
import zoomClasses from "@/shared/ui/map/ZoomControls.module.css";
import { useAudioSettings } from "./audioSettings";
import { AudioSettingsPanel } from "./AudioSettingsPanel";

export function AudioSettingsButton() {
  const [open, setOpen] = useState(false);
  const muted = useAudioSettings((s) => s.muted);
  const label = muted ? "Sound (muted)" : "Sound";
  return (
    <Popover opened={open} onChange={setOpen} position="bottom-end" width={250}>
      <Popover.Target>
        <button
          type="button"
          className={cx(zoomClasses.zoomButton, open && zoomClasses.zoomButtonActive)}
          aria-label={label}
          title={label}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {muted ? <IconVolumeOff size={15} /> : <IconVolume size={15} />}
        </button>
      </Popover.Target>
      <Popover.Dropdown p="sm">
        <AudioSettingsPanel />
      </Popover.Dropdown>
    </Popover>
  );
}
