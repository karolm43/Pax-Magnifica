/**
 * Panel ustawień dźwięku: wyciszenie, suwaki kanałów, następny utwór. JEDEN komponent dla
 * przycisku na mapie (`AudioSettingsButton`) i zakładki „Sound” w Settings (menu i gra).
 */
import { IconPlayerSkipForward } from "@tabler/icons-react";
import { Switch } from "@/ds";
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

export function AudioSettingsPanel({ showSkip = true }: { showSkip?: boolean }) {
  const settings = useAudioSettings();
  return (
    <div className={classes.panel}>
      <Switch
        label="Mute all"
        checked={settings.muted}
        onChange={(e) => settings.set({ muted: e.currentTarget.checked })}
      />
      {SLIDERS.map(({ key, label }) => (
        <label key={key} className={classes.row}>
          <span className={classes.label}>{label}</span>
          <input
            type="range"
            className={classes.range}
            min={0}
            max={100}
            step={5}
            value={Math.round(settings[key] * 100)}
            disabled={settings.muted}
            aria-label={`${label} volume`}
            onChange={(e) => settings.set({ [key]: Number(e.currentTarget.value) / 100 })}
          />
          <span className={classes.value}>{Math.round(settings[key] * 100)}</span>
        </label>
      ))}
      {showSkip && (
        <button type="button" className={classes.skip} onClick={() => skipTrack()}>
          <IconPlayerSkipForward size={14} aria-hidden="true" /> Next track
        </button>
      )}
    </div>
  );
}
