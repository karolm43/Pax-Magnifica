/**
 * Muzyka tła: JEDNA wspólna playlista z `assets/music/` (nie w repo) — wszystkie pliki, także
 * z podfolderów, bez podziału na nastroje (decyzja użytkownika). Losowo bez powtórek w obiegu,
 * płynne przejścia: dwa elementy `<audio>` na zmianę = przenikanie utworów bez dziury.
 */
import { audioTime, connectMediaElement } from "./audioEngine";
import { audioManifest, musicUrl } from "./audioManifest";
import { channelVolume } from "./audioSettings";

/** Wszystkie utwory z manifestu jako jedna lista adresów (eksport dla testów). */
export function buildPlaylist(music: Record<string, string[]>): string[] {
  return Object.entries(music).flatMap(([folder, files]) => files.map((f) => musicUrl(folder, f)));
}

const FADE_S = 2.5;

type Deck = { el: HTMLAudioElement; gain: GainNode | null };

let playlist: string[] = [];
let decks: Deck[] = [];
let active = -1;
let started = false;
/** „Talia” utworów: każdy gra raz na obieg, w losowej kolejności. */
let bag: string[] = [];

function shuffle<T>(list: T[]): T[] {
  const out = [...list];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function nextTrack(): string | null {
  if (playlist.length === 0) return null;
  if (bag.length === 0) bag = shuffle(playlist);
  return bag.shift() ?? null;
}

function makeDeck(): Deck {
  const el = new Audio();
  el.preload = "auto";
  el.crossOrigin = "anonymous";
  const gain = connectMediaElement(el, "music");
  if (gain) gain.gain.value = 0;
  el.addEventListener("ended", () => {
    if (decks[active]?.el === el) playNext();
  });
  el.addEventListener("error", () => {
    if (decks[active]?.el === el) setTimeout(() => playNext(), 1000);
  });
  return { el, gain };
}

function fade(deck: Deck, to: number): void {
  if (deck.gain) {
    const t = audioTime();
    deck.gain.gain.cancelScheduledValues(t);
    deck.gain.gain.setValueAtTime(deck.gain.gain.value, t);
    deck.gain.gain.linearRampToValueAtTime(to, t + FADE_S);
  } else {
    deck.el.volume = to * channelVolume("music");
  }
  if (to === 0) setTimeout(() => deck.el.pause(), FADE_S * 1000 + 100);
}

function playNext(): void {
  const url = nextTrack();
  if (!url) return;
  if (decks.length === 0) decks = [makeDeck(), makeDeck()];
  const previous = decks[active];
  active = (active + 1) % decks.length;
  const deck = decks[active];
  deck.el.src = url;
  void deck.el.play().then(
    () => fade(deck, 1),
    () => {
      // Autoodtwarzanie zablokowane (brak gestu) — spróbujemy przy następnym `startMusic`.
      started = false;
    },
  );
  if (previous) fade(previous, 0);
}

/** Startuje muzykę (wołać po geście gracza). Bez plików w `assets/music/` — nic się nie dzieje. */
export function startMusic(): void {
  if (started) return;
  started = true;
  void audioManifest().then((m) => {
    playlist = buildPlaylist(m.music);
    playNext();
  });
}

/** Pomija bieżący utwór. */
export function skipTrack(): void {
  if (started) playNext();
}

export function stopMusic(): void {
  for (const deck of decks) deck.el.pause();
  started = false;
}
