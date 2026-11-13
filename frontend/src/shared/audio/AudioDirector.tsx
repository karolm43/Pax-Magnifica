/**
 * Reżyser dźwięku strony gry (montowany raz, nic nie rysuje):
 * - globalne dźwięki interfejsu (klik/zakładka/przełącznik),
 * - muzyka tła startuje po pierwszym geście gracza; nastrój z fazy i walki,
 * - kwestie frakcji i transmisje wg NOWYCH wpisów feedu Activity (`voiceCues.ts`).
 * Wpisy obecne przy otwarciu strony nie są nowością (jak w `ActivityToasts`).
 */
import { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { DEFAULT_GAME_ID } from "@/config";
import { fetchJson } from "@/api/fetchJson";
import { useActivityFeed, type BattleView } from "@/api/useBoardEditor";
import { useGameState } from "@/api/useGameState";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { setMusicMood, startMusic, type MusicMood } from "./music";
import { installUiSounds, playUi } from "./uiSounds";
import { battleLines, cuesForEntry, type Cue, type CueContext } from "./voiceCues";
import { hasVoice, loadVoices, sayTransmission, sayVoice } from "./voices";

type Players = Record<string, { faction: string | null; is_bot: boolean }>;

async function playBattle(
  cue: Extract<Cue, { kind: "battle" }>,
  factionOf: (pid: string) => string | null,
  fetchBattle: () => Promise<BattleView | null>,
): Promise<void> {
  const [battle, homes] = await Promise.all([
    fetchBattle(),
    fetchJson<Record<string, string[]>>("/bot/audio/homes", "audio homes").catch(
      () => ({}) as Record<string, string[]>,
    ),
  ]);
  const position = cue.position ?? battle?.position ?? null;
  const defenderHome =
    !!cue.defender && !!position && (homes[cue.defender] ?? []).includes(position);
  const sideOf = (pid: string | null) =>
    battle?.attacker?.playerId === pid
      ? battle.attacker
      : battle?.defender?.playerId === pid
        ? battle.defender
        : null;
  const lines = battleLines(cue.attacker, cue.defender, {
    defenderHome,
    attackerSide: sideOf(cue.attacker),
    defenderSide: sideOf(cue.defender),
    random: Math.random,
  });
  for (const line of lines) {
    const faction = factionOf(line.player);
    if (!sayVoice(faction, line.category)) sayVoice(faction, "battle");
  }
}

export function AudioDirector() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: feed } = useActivityFeed();
  const { data: me } = useNetworkMe();
  const { data: gameState } = useGameState(gameId);
  const queryClient = useQueryClient();
  const seen = useRef<number | null>(null);

  useEffect(() => installUiSounds(), []);

  useEffect(() => {
    void loadVoices();
    const begin = () => startMusic();
    document.addEventListener("pointerdown", begin, { once: true, capture: true });
    document.addEventListener("keydown", begin, { once: true, capture: true });
    return () => {
      document.removeEventListener("pointerdown", begin, { capture: true });
      document.removeEventListener("keydown", begin, { capture: true });
    };
  }, []);

  const phase = gameState?.phase ?? "";
  const inCombat = !!gameState?.activeCombat;
  useEffect(() => {
    const mood: MusicMood = inCombat ? "battle" : phase.startsWith("agenda") ? "agenda" : "ambient";
    setMusicMood(mood);
  }, [phase, inCombat]);

  useEffect(() => {
    if (!feed || me === undefined) return;
    const latest = feed.entries.at(-1)?.seq ?? 0;
    if (seen.current === null || latest < seen.current) {
      seen.current = latest; // pierwszy odczyt albo nowa gra: stare wpisy nie są nowością
      return;
    }
    const since = seen.current;
    seen.current = Math.max(since, latest);
    const players: Players = feed.players;
    const factionOf = (pid: string) => players[pid]?.faction ?? null;
    const ctx: CueContext = {
      me: me.player_id,
      network: me.network,
      isBot: (pid) => players[pid]?.is_bot ?? false,
      factionOf,
      random: Math.random,
    };
    const fresh = feed.entries.filter(
      (e) => e.seq > since && (feed.current_seq === null || e.seq <= feed.current_seq),
    );
    const fetchBattle = () =>
      queryClient
        .fetchQuery<BattleView>({
          queryKey: ["battle"],
          queryFn: () => fetchJson<BattleView>("/bot/tactical/battle", "battle"),
          staleTime: 1000,
        })
        .catch(() => null);
    for (const entry of fresh) {
      for (const cue of cuesForEntry(entry, ctx)) {
        if (cue.kind === "ui") playUi(cue.name);
        else if (cue.kind === "transmission") sayTransmission();
        else if (cue.kind === "battle") void playBattle(cue, factionOf, fetchBattle);
        else {
          const faction = factionOf(cue.player);
          if (hasVoice(faction, cue.category)) sayVoice(faction, cue.category);
          else if (cue.fallback) sayVoice(faction, cue.fallback);
        }
      }
    }
  }, [feed, me, queryClient]);

  return null;
}
