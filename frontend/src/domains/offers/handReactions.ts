/*
 * Karty z ręki (karty akcji, notki) zagrywalne TERAZ w oknie reakcji (RULES.md 54.8). Okno
 * mija z następnym krokiem gry, więc pokazujemy je w karcie „Window open now” obok zdolności
 * „Available now” - widocznej nad oknem walki/inwazji, a nie tylko w zwiniętym doku ręki.
 */

/** Najdłuższa fraza okna, którą jeszcze traktujemy jako „kiedy” (dłuższa = to już efekt). */
const MAX_PHRASE = 120;

/**
 * Fraza okna z tekstu karty: część przed pierwszym dwukropkiem
 * („At the start of an invasion combat: ...” → „At the start of an invasion combat”).
 * ``null``, gdy tekst nie zaczyna się od okna (brak dwukropka albo bardzo długi wstęp).
 */
export function timingPhrase(text: string | null | undefined): string | null {
  if (!text) return null;
  const at = text.indexOf(":");
  if (at <= 0 || at > MAX_PHRASE) return null;
  return text.slice(0, at).trim() || null;
}

type FeedPlayer = { is_bot: boolean };

/**
 * Czyje ręce sprawdzamy. Gra sieciowa: tylko MOJA (ręka jest prywatna, RULES.md 44.2).
 * Lokalnie/solo: każdy człowiek (boty grają karty same, ich okna nie dotyczą ekranu).
 */
export function humanHandOwners(
  me: { network?: boolean; player_id?: string | null } | undefined,
  players: Record<string, FeedPlayer> | undefined,
): string[] {
  if (me?.network) return me.player_id ? [me.player_id] : [];
  return Object.entries(players ?? {})
    .filter(([, p]) => !p.is_bot)
    .map(([id]) => id);
}
