/**
 * Spis plików audio, które NAPRAWDĘ leżą w `assets/` (`GET /audio/manifest`), pytany raz.
 * Pliki serwuje backend pod `/static/...`.
 */

export type AudioManifest = {
  /** `{frakcja: [pliki]}` z `assets/voices/<frakcja>/`. */
  voices: Record<string, string[]>;
  transmissions: string[];
  /** `{nastrój: [pliki]}` z `assets/music/<nastrój>/`; klucz "" = pliki wprost w `assets/music/`. */
  music: Record<string, string[]>;
  ui: string[];
};

const EMPTY: AudioManifest = { voices: {}, transmissions: [], music: {}, ui: [] };

let pending: Promise<AudioManifest> | null = null;

export function audioManifest(): Promise<AudioManifest> {
  pending ??= fetch("/bot/audio/manifest")
    .then((res) => (res.ok ? (res.json() as Promise<Partial<AudioManifest>>) : EMPTY))
    .then((data) => ({ ...EMPTY, ...data }))
    .catch(() => EMPTY);
  return pending;
}

export const voiceUrl = (faction: string, file: string) =>
  `/static/voices/${encodeURIComponent(faction)}/${encodeURIComponent(file)}`;
export const transmissionUrl = (file: string) =>
  `/static/voices/transmissions/${encodeURIComponent(file)}`;
export const musicUrl = (mood: string, file: string) =>
  mood
    ? `/static/music/${encodeURIComponent(mood)}/${encodeURIComponent(file)}`
    : `/static/music/${encodeURIComponent(file)}`;
export const uiUrl = (file: string) => `/static/extra/sfx/ui/${encodeURIComponent(file)}`;
