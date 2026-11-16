/**
 * Dźwięki pola bitwy (czysta prezentacja).
 *
 * PRÓBKI: `assets/extra/sfx/battle/<zdarzenie>-<n>.ogg` (serwowane pod `/static/extra/sfx/…`;
 * spis z `GET /battle/sounds`). Kilka plików jednego zdarzenia to WARIANTY — każde odtworzenie
 * losuje inny niż poprzednio i lekko zmienia wysokość, żeby seria strzałów nie brzmiała jak
 * zacięta płyta. Pochodzenie i licencje (CC0): `assets/extra/sfx/battle/SOURCES.md`.
 * Zdarzenie bez próbki gra awaryjną syntezę WebAudio (`synth`). Wyciszenie w localStorage.
 */

import { channelVolume } from "@/shared/audio/audioSettings";

export type SoundName =
  | "fleetEnter" // flota wlatuje (narastający pomruk silników)
  | "arrive" // zatrzymanie szyku na pozycji (ciężki łoskot)
  | "arriveHeavy" // jw., gdy w szyku jest war sun / flagowiec / dreadnought
  | "laser"
  | "plasma"
  | "flak" // Anti-Fighter Barrage
  | "impact"
  | "explosion"
  | "explosionHeavy"
  | "sustain"
  | "warSunEnter" // war sun wyłania się z wormhole
  | "sunfire" // strzał war suna
  | "missile" // odpalenie rakiety (syk silnika rakietowego)
  | "assaultCannon" // Assault Cannon: ładowanie działa i potężny strzał
  | "retreatHorn" // ogłoszenie odwrotu
  | "retreat" // flota odlatuje z pola bitwy
  | "diceThrow" // garść kości wpada na stół (grzechot)
  | "diceClack" // jedno stuknięcie kostki o stół
  // --- walka naziemna i inwazja ---
  | "rifle" // seria piechoty (karabin automatyczny)
  | "rifleShot" // pojedynczy strzał karabinu
  | "mechCannon" // działo mecha
  | "groundBlast" // wybuch pocisku na ziemi
  | "bulletHit" // kula trafia piechotę / ziemię
  | "armorHit" // pocisk trafia pancerz mecha (także Sustain Damage mecha)
  | "infantryDeath" // okrzyk ginącego żołnierza
  | "bodyFall" // ciało pada na ziemię
  | "mechPowerDown" // gasnące serwa i reaktor mecha
  | "mechCollapse" // kadłub mecha wali się na ziemię
  | "mechStep" // ciężki krok / przysiad mecha
  | "dropPod" // kapsuła desantowa spada z orbity
  | "podLand"; // kapsuła uderza w ziemię

export type SoundOpts = {
  /** Panorama stereo −1 (lewo) … 1 (prawo). */
  pan?: number;
  /** Cięższa wersja (niższy ton, dłuższy wybrzmiew) — duże okręty. */
  heavy?: boolean;
  /** Głośność względna 0..1. */
  gain?: number;
};

const SFX_BASE = "/static/extra/sfx";
const STORAGE_KEY = "battle.sound.muted";
const MASTER = 0.5;
/** Próbki są znormalizowane do szczytu −1 dB — ciszej niż synteza, żeby nie zagłuszały muzyki. */
const SAMPLE_GAIN = 0.8;

let ctx: AudioContext | null = null;
let muted =
  typeof localStorage !== "undefined" &&
  localStorage.getItem(STORAGE_KEY) === "1";
/** Zdarzenie -> zdekodowane warianty (pusta lista = brak próbek, gra synteza). */
const samples = new Map<string, AudioBuffer[]>();
const lastVariant = new Map<string, number>();
let loadStarted = false;
let noiseBuffer: AudioBuffer | null = null;

/**
 * Zdarzenia bez własnej syntezy: przy braku próbki grają najbliższy dźwięk syntezowany
 * (`null` = cisza — syntetyczny okrzyk czy szum serw brzmiałyby gorzej niż nic).
 */
const SYNTH_FALLBACK: Partial<Record<SoundName, SoundName | null>> = {
  rifle: "flak",
  rifleShot: "flak",
  mechCannon: "plasma",
  groundBlast: "explosion",
  bulletHit: "impact",
  armorHit: "impact",
  infantryDeath: null,
  bodyFall: "arrive",
  mechPowerDown: null,
  mechCollapse: "arriveHeavy",
  mechStep: "arrive",
  dropPod: "retreat",
  podLand: "arrive",
};

export function isBattleMuted(): boolean {
  return muted;
}

export function setBattleMuted(value: boolean): void {
  muted = value;
  try {
    localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
  } catch {
    // brak localStorage — trudno, zostaje w pamięci
  }
}

function audio(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

function noise(c: AudioContext): AudioBuffer {
  if (!noiseBuffer) {
    noiseBuffer = c.createBuffer(1, c.sampleRate * 2, c.sampleRate);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  }
  return noiseBuffer;
}

/** Nazwa zdarzenia z nazwy pliku: `battle/rifle-2.ogg` -> `rifle`. Eksport dla testów. */
export function soundOfFile(file: string): string {
  const base = file.split("/").pop() ?? file;
  return base.replace(/\.[^.]+$/, "").replace(/-\d+$/, "");
}

/** Grupuje pliki z `GET /battle/sounds` po zdarzeniu (stary format: same nazwy `.mp3`). */
export function groupSampleFiles(data: {
  sounds?: string[];
  files?: string[];
}): Map<string, string[]> {
  const files = data.files ?? (data.sounds ?? []).map((n) => `${n}.mp3`);
  const out = new Map<string, string[]>();
  for (const file of files) {
    const name = soundOfFile(file);
    out.set(name, [...(out.get(name) ?? []), file]);
  }
  return out;
}

/**
 * Wczytuje próbki leżące NAPRAWDĘ w `assets/extra/sfx/` (`GET /battle/sounds`, pytane raz) —
 * bez tej listy każdy brak byłby czerwonym 404 w konsoli przeglądarki.
 */
export function preloadBattleSounds(): void {
  const c = audio();
  if (!c || loadStarted) return;
  loadStarted = true;
  void fetch("/bot/battle/sounds")
    .then((res) =>
      res.ok
        ? (res.json() as Promise<{ sounds?: string[]; files?: string[] }>)
        : {},
    )
    .catch(() => ({}))
    .then((data) => {
      for (const [name, files] of groupSampleFiles(data)) {
        const list: AudioBuffer[] = [];
        samples.set(name, list);
        for (const file of files) {
          void fetch(`${SFX_BASE}/${file}`)
            .then((res) => {
              if (!res.ok) throw new Error("no sample");
              return res.arrayBuffer();
            })
            .then((buf) => c.decodeAudioData(buf))
            .then((decoded) => list.push(decoded))
            .catch(() => undefined);
        }
      }
    });
}

/** Losuje wariant inny niż ostatnio zagrany (przy jednym wariancie — zawsze ten). Eksport dla testów. */
export function pickVariant(
  name: string,
  count: number,
  random: () => number = Math.random,
): number {
  if (count <= 1) return 0;
  const last = lastVariant.get(name) ?? -1;
  let n = Math.floor(random() * (last >= 0 ? count - 1 : count));
  if (last >= 0 && n >= last) n += 1;
  lastVariant.set(name, n);
  return n;
}

type Out = { c: AudioContext; out: AudioNode; t: number };

/** Węzeł wyjściowy z panoramą i głośnością głównego regulatora. */
function output(c: AudioContext, opts: SoundOpts): AudioNode {
  const master = c.createGain();
  // Suwak „Battle effects” i głośność ogólna z ustawień dźwięku (`shared/audio`).
  master.gain.value = MASTER * channelVolume("effects") * (opts.gain ?? 1);
  let tail: AudioNode = master;
  if (opts.pan !== undefined && typeof c.createStereoPanner === "function") {
    const pan = c.createStereoPanner();
    pan.pan.value = Math.max(-1, Math.min(1, opts.pan));
    pan.connect(master);
    tail = pan;
  }
  master.connect(c.destination);
  return tail;
}

function env(
  g: GainNode,
  t: number,
  peak: number,
  attack: number,
  decay: number,
): void {
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(peak, t + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
}

function tone(
  { c, out, t }: Out,
  type: OscillatorType,
  f0: number,
  f1: number,
  peak: number,
  attack: number,
  decay: number,
): void {
  const osc = c.createOscillator();
  const g = c.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(f0, t);
  osc.frequency.exponentialRampToValueAtTime(
    Math.max(20, f1),
    t + attack + decay,
  );
  env(g, t, peak, attack, decay);
  osc.connect(g).connect(out);
  osc.start(t);
  osc.stop(t + attack + decay + 0.05);
}

function burst(
  { c, out, t }: Out,
  filter: BiquadFilterType,
  f0: number,
  f1: number,
  peak: number,
  attack: number,
  decay: number,
): void {
  const src = c.createBufferSource();
  src.buffer = noise(c);
  const flt = c.createBiquadFilter();
  flt.type = filter;
  flt.frequency.setValueAtTime(f0, t);
  flt.frequency.exponentialRampToValueAtTime(
    Math.max(20, f1),
    t + attack + decay,
  );
  const g = c.createGain();
  env(g, t, peak, attack, decay);
  src.connect(flt).connect(g).connect(out);
  src.start(t);
  src.stop(t + attack + decay + 0.05);
}

function synth(name: SoundName, o: Out, heavy: boolean): void {
  const k = heavy ? 0.6 : 1; // mnożnik wysokości dźwięku
  const len = heavy ? 1.5 : 1; // mnożnik długości
  switch (name) {
    case "fleetEnter":
      burst(o, "lowpass", 90, 260, 0.5, 1.8, 2.6);
      tone(o, "sawtooth", 46, 70, 0.14, 2.0, 2.4);
      tone(o, "triangle", 92, 120, 0.08, 2.2, 2.2);
      break;
    case "arrive":
      tone(o, "sine", 90, 38, 0.8, 0.01, 0.7);
      burst(o, "lowpass", 400, 60, 0.35, 0.01, 0.5);
      break;
    case "arriveHeavy":
      tone(o, "sine", 62, 26, 1, 0.01, 1.4);
      burst(o, "lowpass", 300, 40, 0.5, 0.01, 1.1);
      tone(o, "sawtooth", 55, 34, 0.18, 0.02, 1.3);
      break;
    case "laser":
      tone(o, "sawtooth", 2200 * k, 320 * k, 0.16, 0.005, 0.28 * len);
      tone(o, "square", 1100 * k, 160 * k, 0.05, 0.005, 0.22 * len);
      break;
    case "plasma":
      tone(o, "sine", 340 * k, 90 * k, 0.4, 0.01, 0.42 * len);
      burst(o, "bandpass", 1400 * k, 300 * k, 0.1, 0.01, 0.3 * len);
      break;
    case "flak":
      for (let i = 0; i < 3; i++) {
        burst(
          { ...o, t: o.t + i * 0.055 },
          "highpass",
          3200,
          2200,
          0.12,
          0.002,
          0.04,
        );
      }
      break;
    case "impact":
      burst(o, "lowpass", 2400, 140, 0.5, 0.004, 0.32 * len);
      tone(o, "sine", 130 * k, 44, 0.55, 0.004, 0.3 * len);
      break;
    case "explosion":
      burst(o, "lowpass", 3200, 70, 0.8, 0.01, 1.2);
      tone(o, "sine", 100, 34, 0.7, 0.01, 1.0);
      break;
    case "explosionHeavy":
      burst(o, "lowpass", 2600, 45, 1, 0.01, 2.4);
      tone(o, "sine", 70, 22, 1, 0.01, 2.0);
      tone(o, "sawtooth", 60, 28, 0.2, 0.02, 1.8);
      break;
    case "retreatHorn":
      // dwa opadające sygnały — „wycofać się"
      tone(o, "triangle", 520, 500, 0.22, 0.02, 0.32);
      tone({ ...o, t: o.t + 0.38 }, "triangle", 390, 360, 0.22, 0.02, 0.5);
      break;
    case "retreat":
      // narastający świst silników na pełnej mocy, który oddala się i cichnie
      burst(o, "bandpass", 260, 2600, 0.45, 1.1, 1.4);
      tone(o, "sawtooth", 70, 240, 0.12, 1.2, 1.2);
      tone(o, "sine", 140, 420, 0.18, 1.0, 1.3);
      break;
    case "sunfire":
      tone(o, "sine", 220, 50, 0.6, 0.02, 0.9);
      burst(o, "lowpass", 1600, 90, 0.45, 0.02, 0.9);
      tone(o, "sawtooth", 110, 40, 0.12, 0.05, 0.8);
      break;
    case "missile":
      // syk startu: szum pasmowy, który rośnie i ucieka w górę, plus niski „pchnięcie"
      burst(o, "bandpass", 700 * k, 2600 * k, 0.22, 0.03, 0.55 * len);
      tone(o, "sawtooth", 160 * k, 90 * k, 0.06, 0.01, 0.35 * len);
      break;
    case "assaultCannon":
      // ładowanie (narastający ton) → huk wystrzału z długim pogłosem
      tone(o, "sine", 120, 900, 0.18, 0.75, 0.05);
      burst(o, "bandpass", 300, 2400, 0.16, 0.75, 0.05);
      tone({ ...o, t: o.t + 0.8 }, "sine", 90, 26, 1, 0.005, 1.6);
      burst({ ...o, t: o.t + 0.8 }, "lowpass", 4200, 60, 0.9, 0.005, 1.5);
      tone({ ...o, t: o.t + 0.8 }, "sawtooth", 70, 30, 0.22, 0.01, 1.2);
      break;
    case "warSunEnter":
      // zasysający wir, potem głęboki „wydech" przejścia
      burst(o, "bandpass", 200, 1800, 0.35, 1.4, 0.6);
      tone(o, "sine", 60, 420, 0.25, 1.5, 0.5);
      tone({ ...o, t: o.t + 1.7 }, "sine", 80, 24, 1, 0.01, 1.8);
      burst({ ...o, t: o.t + 1.7 }, "lowpass", 1800, 40, 0.6, 0.01, 1.6);
      break;
    case "diceThrow":
      // grzechot kilku kostek w garści i wpadnięcie na stół
      for (let i = 0; i < 5; i++) {
        burst(
          { ...o, t: o.t + i * 0.06 },
          "bandpass",
          2200 - i * 150,
          1400,
          0.1,
          0.003,
          0.05,
        );
      }
      break;
    case "diceClack":
      // krótkie, twarde stuknięcie plastiku o drewno
      burst(o, "highpass", 3000, 1800, 0.34, 0.001, 0.03);
      tone(o, "triangle", 950, 430, 0.14, 0.001, 0.045);
      break;
    case "sustain":
      tone(o, "sine", 620, 1500, 0.22, 0.02, 0.5);
      tone(o, "triangle", 930, 2200, 0.1, 0.02, 0.45);
      burst(o, "highpass", 5000, 8000, 0.05, 0.02, 0.35);
      break;
  }
}

/** Odtwarza dźwięk (próbka z pliku, jeśli jest; inaczej synteza). Cicho ignoruje błędy. */
export function playBattleSound(name: SoundName, opts: SoundOpts = {}): void {
  if (muted) return;
  const c = audio();
  if (!c) return;
  if (!loadStarted) preloadBattleSounds();
  try {
    const variants = samples.get(name) ?? [];
    if (variants.length > 0) {
      const out = output(c, { ...opts, gain: (opts.gain ?? 1) * SAMPLE_GAIN });
      const src = c.createBufferSource();
      src.buffer = variants[pickVariant(name, variants.length)];
      // ±5% wysokości — kolejne strzały serii nie są identyczne; ciężkie jednostki niżej.
      src.playbackRate.value =
        (opts.heavy ? 0.88 : 1) * (0.95 + Math.random() * 0.1);
      src.connect(out);
      src.start();
      return;
    }
    const synthName = name in SYNTH_FALLBACK ? SYNTH_FALLBACK[name] : name;
    if (!synthName) return;
    synth(synthName, { c, out: output(c, opts), t: c.currentTime }, opts.heavy ?? false);
  } catch {
    // dźwięk to dodatek — nigdy nie psuje walki
  }
}
