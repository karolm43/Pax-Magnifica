/**
 * Muzyka tła: playlista z `assets/music/` (nie w repo), losowo bez powtórek, płynne przejścia.
 *
 * Nastrój wybiera gra (`setMusicMood`): `battle` w trakcie walki, `agenda` w fazie agendy, poza
 * tym `ambient`. Podfoldery `assets/music/<nazwa>/` przypisujemy do nastroju po nazwie
 * (`musicMoodOf`); pliki wprost w `assets/music/` i nieznane foldery = `ambient`. Gdy dla nastroju
 * nie ma utworów, gra `ambient` (a gdy i tego brak — cokolwiek jest).
 * Dwa elementy `<audio>` na zmianę = przenikanie utworów bez dziury.
 */
import { audioTime, connectMediaElement } from "./audioEngine";
import { audioManifest, musicUrl } from "./audioManifest";
import { channelVolume } from "./audioSettings";

export type MusicMood = "ambient" | "battle" | "agenda";

/** Nastrój podfolderu po nazwie (eksport dla testów). */
export function musicMoodOf(folder: string): MusicMood {
  const name = folder.toLowerCase();
  if (/^(bitw|battle|combat|walk|war|fight)/.test(name)) return "battle";
  if (/^(agend|rada|council|napi|tension|polit)/.test(name)) return "agenda";
  return "ambient";
}

export type Playlists = Record<MusicMood, string[]>;

export function buildPlaylists(music: Record<string, string[]>): Playlists {
  const lists: Playlists = { ambient: [], battle: [], agenda: [] };
  for (const [folder, files] of Object.entries(music)) {
    const mood = folder ? musicMoodOf(folder) : "ambient";
    lists[mood].push(...files.map((f) => musicUrl(folder, f)));
  }
  return lists;
}

/** Utwory dla nastroju z rezerwą (eksport dla testów). */
export function tracksFor(lists: Playlists, mood: MusicMood): string[] {
  if (lists[mood].length) return lists[mood];
  if (lists.ambient.length) return lists.ambient;
  return [...lists.battle, ...lists.agenda];
}

const FADE_S = 2.5;

type Deck = { el: HTMLAudioElement; gain: GainNode | null };

let lists: Playlists | null = null;
let decks: Deck[] = [];
let active = -1;
let mood: MusicMood = "ambient";
let playingMood: MusicMood | null = null;
let started = false;
/** Kolejka „talii” per nastrój: utwory grają w losowej kolejności, każdy raz na obieg. */
const bags = new Map<MusicMood, string[]>();

function shuffle<T>(list: T[]): T[] {
  const out = [...list];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function nextTrack(forMood: MusicMood): string | null {
  if (!lists) return null;
  const pool = tracksFor(lists, forMood);
  if (pool.length === 0) return null;
  let bag = bags.get(forMood);
  if (!bag || bag.length === 0) {
    bag = shuffle(pool);
    bags.set(forMood, bag);
  }
  return bag.shift() ?? null;
}

function makeDeck(): Deck {
  const el = new Audio();
  el.preload = "auto";
  el.crossOrigin = "anonymous";
  const gain = connectMediaElement(el, "music");
  if (gain) gain.gain.value = 0;
  el.addEventListener("ended", () => {
    if (decks[active]?.el === el) playNext(mood);
  });
  el.addEventListener("error", () => {
    if (decks[active]?.el === el) setTimeout(() => playNext(mood), 1000);
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

function playNext(forMood: MusicMood): void {
  const url = nextTrack(forMood);
  if (!url) return;
  if (decks.length === 0) decks = [makeDeck(), makeDeck()];
  const previous = decks[active];
  active = (active + 1) % decks.length;
  const deck = decks[active];
  deck.el.src = url;
  playingMood = forMood;
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
    lists = buildPlaylists(m.music);
    playNext(mood);
  });
}

/** Zmiana nastroju: przenikanie do utworu z innej puli (ten sam nastrój = bez zmian). */
export function setMusicMood(next: MusicMood): void {
  mood = next;
  if (!started || !lists || playingMood === null) return;
  const samePool = tracksFor(lists, next) === tracksFor(lists, playingMood);
  if (playingMood !== next && !samePool) playNext(next);
  else playingMood = next;
}

/** Pomija bieżący utwór. */
export function skipTrack(): void {
  if (started) playNext(mood);
}

export function stopMusic(): void {
  for (const deck of decks) deck.el.pause();
  started = false;
  playingMood = null;
}
