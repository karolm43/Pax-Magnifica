/**
 * Wspólny silnik dźwięku: JEDEN `AudioContext`, węzeł głośności na kanał i pamięć próbek.
 *
 * Krótkie pliki (UI, kwestie frakcji) dekodujemy do `AudioBuffer` (granie bez opóźnień, wiele
 * naraz). Muzyka idzie przez `<audio>` podpięte do kanału (`connectMediaElement`) — strumień,
 * bez dekodowania całych utworów do pamięci. Głośność kanałów śledzi `useAudioSettings`.
 * Przeglądarka odblokowuje dźwięk dopiero po geście gracza — do tego czasu wszystko milczy.
 */
import { channelVolume, useAudioSettings, type AudioChannel } from "./audioSettings";

const CHANNELS: AudioChannel[] = ["music", "voices", "ui", "effects"];

let ctx: AudioContext | null = null;
const gains = new Map<AudioChannel, GainNode>();
const buffers = new Map<string, Promise<AudioBuffer | null>>();
/** Mnożnik kanału muzyki na czas kwestii (ściszenie pod głos). */
let musicDuck = 1;

function context(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    try {
      ctx = new Ctor();
    } catch {
      return null;
    }
    for (const channel of CHANNELS) {
      const g = ctx.createGain();
      g.connect(ctx.destination);
      gains.set(channel, g);
    }
    applyVolumes();
    useAudioSettings.subscribe(() => applyVolumes());
  }
  return ctx;
}

function applyVolumes(): void {
  if (!ctx) return;
  for (const channel of CHANNELS) {
    const g = gains.get(channel);
    if (!g) continue;
    const target = channelVolume(channel) * (channel === "music" ? musicDuck : 1);
    g.gain.setTargetAtTime(target, ctx.currentTime, 0.08);
  }
}

/** Czy przeglądarka już pozwala grać (był gest gracza). */
export function audioUnlocked(): boolean {
  return ctx?.state === "running";
}

/** Wznawia kontekst — wołać z obsługi gestu gracza (klik, klawisz). */
export function unlockAudio(): void {
  const c = context();
  if (c && c.state === "suspended") void c.resume().catch(() => undefined);
}

/** Ściszenie muzyki pod kwestię (1 = normalnie). */
export function setMusicDuck(value: number): void {
  musicDuck = Math.max(0, Math.min(1, value));
  applyVolumes();
}

function loadBuffer(url: string): Promise<AudioBuffer | null> {
  const c = context();
  if (!c) return Promise.resolve(null);
  let pending = buffers.get(url);
  if (!pending) {
    pending = fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`audio ${res.status}`);
        return res.arrayBuffer();
      })
      .then((data) => c.decodeAudioData(data))
      .catch(() => null);
    buffers.set(url, pending);
  }
  return pending;
}

/** Wczytuje próbki z wyprzedzeniem (np. dźwięki UI), żeby pierwszy klik nie czekał. */
export function preloadAudio(urls: string[]): void {
  for (const url of urls) void loadBuffer(url);
}

export type PlayOptions = { gain?: number; rate?: number };

/**
 * Gra plik na kanale. Zwraca obietnicę spełnioną po zakończeniu (false = nie zagrało:
 * brak pliku, zablokowany dźwięk, kanał wyciszony).
 */
export async function playFile(
  url: string,
  channel: AudioChannel,
  opts: PlayOptions = {},
): Promise<boolean> {
  const c = context();
  if (!c || c.state !== "running" || channelVolume(channel) <= 0) return false;
  const buffer = await loadBuffer(url);
  const out = gains.get(channel);
  if (!buffer || !out) return false;
  const src = c.createBufferSource();
  src.buffer = buffer;
  if (opts.rate) src.playbackRate.value = opts.rate;
  const g = c.createGain();
  g.gain.value = opts.gain ?? 1;
  src.connect(g).connect(out);
  return new Promise((resolve) => {
    src.onended = () => resolve(true);
    src.start();
  });
}

/** Podpina element `<audio>` pod kanał (muzyka). Null, gdy WebAudio niedostępne. */
export function connectMediaElement(el: HTMLMediaElement, channel: AudioChannel): GainNode | null {
  const c = context();
  const out = gains.get(channel);
  if (!c || !out) return null;
  try {
    const src = c.createMediaElementSource(el);
    const g = c.createGain();
    src.connect(g).connect(out);
    return g;
  } catch {
    return null;
  }
}

/** Bieżący czas kontekstu (do płynnych przejść). */
export function audioTime(): number {
  return ctx?.currentTime ?? 0;
}
