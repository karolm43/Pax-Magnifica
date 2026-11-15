/**
 * Dźwięki interfejsu (paczka Kenney „Interface Sounds”, CC0 — `assets/extra/sfx/ui/`).
 *
 * `installUiSounds()` montuje JEDEN globalny nasłuch: klik w przycisk/zakładkę/link daje „click”
 * bez dopisywania czegokolwiek w komponentach. Element może nadpisać dźwięk atrybutem
 * `data-sound="<nazwa>"` albo go wyłączyć: `data-sound="none"` (działa też na przodku).
 * Pozostałe zdarzenia (tura, błąd, upuszczenie karty…) woła kod przez `playUi(nazwa)`.
 */
import { playFile, preloadAudio, unlockAudio } from "./audioEngine";
import { audioManifest, uiUrl } from "./audioManifest";

export type UiSound =
  | "click"
  | "select"
  | "open"
  | "close"
  | "confirm"
  | "error"
  | "drop"
  | "transition"
  | "turn"
  | "notify"
  | "tick";

/** Nazwa dźwięku -> plik (z manifestu; brak pliku = cisza). */
let files: Map<string, string> | null = null;
const lastPlayed = new Map<UiSound, number>();
/** Ten sam dźwięk nie częściej niż co tyle ms (seria klików, podwójne zdarzenia). */
const MIN_GAP_MS = 60;

function loadFiles(): void {
  if (files) return;
  files = new Map();
  void audioManifest().then((m) => {
    for (const file of m.ui) files?.set(file.replace(/\.[^.]+$/, ""), file);
    preloadAudio(m.ui.map(uiUrl));
  });
}

export function playUi(name: UiSound, gain = 1): void {
  loadFiles();
  const file = files?.get(name);
  if (!file) return;
  const now = performance.now();
  if (now - (lastPlayed.get(name) ?? 0) < MIN_GAP_MS) return;
  lastPlayed.set(name, now);
  void playFile(uiUrl(file), "ui", { gain });
}

const CLICKABLE =
  'button, [role="button"], [role="tab"], [role="menuitem"], [role="option"], [role="switch"], [role="checkbox"], [role="radio"], a[href], summary, input[type="checkbox"], input[type="radio"], select';

/** Jaki dźwięk dać za klik w ten element (null = żaden). Eksport dla testów. */
export function soundForClick(target: Element | null): UiSound | null {
  if (!target) return null;
  const muted = target.closest("[data-sound]");
  const el = target.closest(CLICKABLE);
  if (muted && (!el || muted.contains(el))) {
    const value = muted.getAttribute("data-sound");
    if (value === "none") return null;
    if (value) return value as UiSound;
  }
  if (!el) return null;
  if (el.matches(":disabled, [aria-disabled='true']")) return null;
  const role = el.getAttribute("role");
  if (role === "tab" || role === "option" || el.tagName === "SELECT") return "select";
  if (
    role === "switch" ||
    role === "checkbox" ||
    role === "radio" ||
    (el instanceof HTMLInputElement && (el.type === "checkbox" || el.type === "radio"))
  ) {
    // Przełączniki: cichy „tick” (dawny toggle.ogg był nieprzyjemny — usunięty, decyzja użytkownika).
    return "tick";
  }
  return "click";
}

let installed = false;

/** Globalny nasłuch kliknięć (raz na stronę). Zwraca funkcję sprzątającą. */
export function installUiSounds(): () => void {
  if (installed || typeof document === "undefined") return () => undefined;
  installed = true;
  loadFiles();
  const unlock = () => unlockAudio();
  const onClick = (event: MouseEvent) => {
    const sound = soundForClick(event.target instanceof Element ? event.target : null);
    if (sound) playUi(sound, sound === "tick" ? 0.6 : 1);
  };
  document.addEventListener("pointerdown", unlock, true);
  document.addEventListener("keydown", unlock, true);
  document.addEventListener("click", onClick, true);
  return () => {
    installed = false;
    document.removeEventListener("pointerdown", unlock, true);
    document.removeEventListener("keydown", unlock, true);
    document.removeEventListener("click", onClick, true);
  };
}
