/**
 * Kwestie frakcji (`assets/voices/<frakcja>/`) i transmisje (`assets/voices/transmissions/`).
 *
 * Kategoria pliku = nazwa bez cyfr i znaków (`battle-3.mp3` -> `battle`, `home-defense-2` ->
 * `homedefense`, `OrbitalDrop4` -> `orbitaldrop`); `special`, `specialb`, `special11` -> `special`.
 * Kwestie lecą PO KOLEI (jeden głos naraz, krótka kolejka), muzyka ścisza się pod głos.
 */
import { playFile, setMusicDuck } from "./audioEngine";
import { audioManifest, transmissionUrl, voiceUrl } from "./audioManifest";

export type VoiceCategory = string;

/** Kategoria kwestii z nazwy pliku (eksport dla testów). */
export function voiceCategory(file: string): VoiceCategory {
  const key = file.replace(/\.[^.]+$/, "").toLowerCase().replace(/[^a-z]/g, "");
  return /^special[a-z]?$/.test(key) ? "special" : key;
}

/** `{frakcja: {kategoria: [pliki]}}`. */
export type VoiceBank = Record<string, Record<VoiceCategory, string[]>>;

export function buildVoiceBank(voices: Record<string, string[]>): VoiceBank {
  const bank: VoiceBank = {};
  for (const [faction, list] of Object.entries(voices)) {
    const byCategory: Record<string, string[]> = {};
    for (const file of list) (byCategory[voiceCategory(file)] ??= []).push(file);
    bank[faction] = byCategory;
  }
  return bank;
}

let bank: VoiceBank = {};
let transmissions: string[] = [];
let loaded: Promise<void> | null = null;

export function loadVoices(): Promise<void> {
  loaded ??= audioManifest().then((m) => {
    bank = buildVoiceBank(m.voices);
    transmissions = m.transmissions;
  });
  return loaded;
}

export function hasVoice(faction: string | null | undefined, category: VoiceCategory): boolean {
  return !!faction && (bank[faction]?.[category]?.length ?? 0) > 0;
}

/** Ostatnio zagrany plik per (frakcja, kategoria) — żeby ta sama kwestia nie leciała dwa razy z rzędu. */
const lastPick = new Map<string, string>();

function pick(key: string, list: string[], random: () => number): string {
  const prev = lastPick.get(key);
  const pool = list.length > 1 ? list.filter((f) => f !== prev) : list;
  const choice = pool[Math.floor(random() * pool.length)] ?? list[0];
  lastPick.set(key, choice);
  return choice;
}

type Line = { url: string };
const queue: Line[] = [];
let speaking = false;
/** Maks. kwestii czekających — przy lawinie zdarzeń (bot gra szybko) starsze przepadają. */
const MAX_QUEUE = 2;
/** Przerwa między kwestiami (ms). */
const GAP_MS = 350;
/** Muzyka pod głosem: tyle głośności zostaje. */
const DUCK = 0.35;

async function drain(): Promise<void> {
  if (speaking) return;
  speaking = true;
  setMusicDuck(DUCK);
  try {
    while (queue.length > 0) {
      const line = queue.shift();
      if (line) await playFile(line.url, "voices");
      await new Promise((r) => setTimeout(r, GAP_MS));
    }
  } finally {
    speaking = false;
    setMusicDuck(1);
  }
}

function enqueue(url: string): void {
  queue.push({ url });
  while (queue.length > MAX_QUEUE) queue.shift();
  void drain();
}

/** Nazwa pliku bez rozszerzenia, małymi literami (`Battle1.mp3` -> `battle1`). */
const stem = (file: string) => file.replace(/\.[^.]+$/, "").toLowerCase();

/**
 * Gra kwestię frakcji z kategorii: konkretne nagranie `file` (gdy jest), inaczej losowe.
 * False = brak nagrań w tej kategorii.
 */
export function sayVoice(
  faction: string | null | undefined,
  category: VoiceCategory,
  random: () => number = Math.random,
  file?: string,
): boolean {
  const list = faction ? bank[faction]?.[category] : undefined;
  if (!faction || !list?.length) return false;
  const exact = file ? list.find((f) => stem(f) === file.toLowerCase()) : undefined;
  enqueue(voiceUrl(faction, exact ?? pick(`${faction}/${category}`, list, random)));
  return true;
}

/** Gra losową „transmisję” (wiadomość od innego gracza, Rada Galaktyczna). */
export function sayTransmission(random: () => number = Math.random): boolean {
  if (transmissions.length === 0) return false;
  enqueue(transmissionUrl(pick("transmissions", transmissions, random)));
  return true;
}
