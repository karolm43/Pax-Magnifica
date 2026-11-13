/**
 * Przycisk dźwięku w pływającym pasku mapy (obok Events): wyciszenie + suwaki kanałów.
 * Wygląd przycisku = `zoomButton` (jak sąsiednie), panel = `Popover` z design systemu.
 */
import { useState } from "react";
import cx from "clsx";
import { IconPlayerSkipForward, IconVolume, IconVolumeOff } from "@tabler/icons-react";
import { Popover, Switch } from "@/ds";
import zoomClasses from "@/shared/ui/map/ZoomControls.module.css";
import { useAudioSettings, type AudioSettings } from "./audioSettings";
import { skipTrack } from "./music";
import classes from "./AudioSettingsButton.module.css";

const SLIDERS: { key: keyof Omit<AudioSettings, "muted">; label: string }[] = [
  { key: "master", label: "Master" },
  { key: "music", label: "Music" },
  { key: "voices", label: "Faction voices" },
  { key: "effects", label: "Battle effects" },
  { key: "ui", label: "Interface" },
];

export function AudioSettingsButton() {
  const [open, setOpen] = useState(false);
  const settings = useAudioSettings();
  const label = settings.muted ? "Sound (muted)" : "Sound";
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
          {settings.muted ? <IconVolumeOff size={15} /> : <IconVolume size={15} />}
        </button>
      </Popover.Target>
      <Popover.Dropdown p="sm">
        <div className={classes.panel}>
          <Switch
            label="Mute all"
            checked={settings.muted}
            onChange={(e) => settings.set({ muted: e.currentTarget.checked })}
          />
          {SLIDERS.map(({ key, label: text }) => (
            <label key={key} className={classes.row}>
              <span className={classes.label}>{text}</span>
              <input
                type="range"
                className={classes.range}
                min={0}
                max={100}
                step={5}
                value={Math.round(settings[key] * 100)}
                disabled={settings.muted}
                aria-label={`${text} volume`}
                onChange={(e) => settings.set({ [key]: Number(e.currentTarget.value) / 100 })}
              />
              <span className={classes.value}>{Math.round(settings[key] * 100)}</span>
            </label>
          ))}
          <button type="button" className={classes.skip} onClick={() => skipTrack()}>
            <IconPlayerSkipForward size={14} aria-hidden="true" /> Next track
          </button>
        </div>
      </Popover.Dropdown>
    </Popover>
  );
}
