/**
 * Ustawienia dźwięku gracza (per przeglądarka): głośność ogólna i kanałów + wyciszenie.
 *
 * Kanały: `music` (muzyka tła), `voices` (kwestie frakcji, transmisje), `ui` (kliknięcia,
 * przejścia), `effects` (pole bitwy — `battleSound.ts`). Zapis w localStorage to tylko wygoda
 * widza; każdy odczyt/zapis w try/catch (tryb prywatny, zablokowane dane strony).
 */
import { create } from "zustand";

export type AudioChannel = "music" | "voices" | "ui" | "effects";

export type AudioSettings = {
  master: number;
  music: number;
  voices: number;
  ui: number;
  effects: number;
  muted: boolean;
};

const STORAGE_KEY = "audio.settings";

export const DEFAULT_AUDIO_SETTINGS: AudioSettings = {
  master: 0.7,
  music: 0.5,
  voices: 0.8,
  ui: 0.5,
  effects: 0.7,
  muted: false,
};

function clamp01(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.max(0, Math.min(1, value))
    : fallback;
}

function load(): AudioSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_AUDIO_SETTINGS;
    const data = JSON.parse(raw) as Partial<AudioSettings>;
    const d = DEFAULT_AUDIO_SETTINGS;
    return {
      master: clamp01(data.master, d.master),
      music: clamp01(data.music, d.music),
      voices: clamp01(data.voices, d.voices),
      ui: clamp01(data.ui, d.ui),
      effects: clamp01(data.effects, d.effects),
      muted: data.muted === true,
    };
  } catch {
    return DEFAULT_AUDIO_SETTINGS;
  }
}

type Store = AudioSettings & {
  set: (patch: Partial<AudioSettings>) => void;
};

export const useAudioSettings = create<Store>((setState, get) => ({
  ...load(),
  set: (patch) => {
    setState(patch);
    const { set: _set, ...settings } = get();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // brak localStorage — ustawienia zostają tylko w pamięci
    }
  },
}));

/**
 * Stałe ściszenie kanałów (pliki źródłowe są głośne): nawet suwak na 100 nie „krzyczy”.
 * Dobrane na ucho — decyzja użytkownika „wszystko jest za głośne”.
 */
const CHANNEL_TRIM: Record<AudioChannel, number> = {
  music: 0.6,
  voices: 0.8,
  ui: 0.35,
  effects: 0.6,
};

/**
 * Suwak -> wzmocnienie: ucho słyszy głośność logarytmicznie, więc liniowy suwak na 50 brzmiał
 * prawie jak na 100. Krzywa kwadratowa: 50 ≈ -12 dB, 25 ≈ -24 dB.
 */
const perceptual = (v: number) => v * v;

/** Skuteczna głośność kanału 0..1 (z głośnością ogólną, krzywą słuchu i wyciszeniem). */
export function channelVolume(channel: AudioChannel, s: AudioSettings = useAudioSettings.getState()): number {
  if (s.muted) return 0;
  return perceptual(s.master) * perceptual(s[channel]) * CHANNEL_TRIM[channel];
}
