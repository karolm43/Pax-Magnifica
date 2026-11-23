import { useEffect, useMemo } from "react";
import { useActivityFeed } from "@/api/useBoardEditor";
import { useActivityContext } from "../game-shell/components/ActivityPanel/useActivityContext";
import { buildChronicle, type ChronicleChapter } from "./buildChronicle";
import { useChronicleStore } from "./useChronicleStore";

/** Księga zbudowana z feedu Activity bieżącej gry (puste, dopóki feed się nie wczyta). */
export function useChronicle(): {
  chapters: ChronicleChapter[];
  players: ReturnType<typeof useActivityContext>["players"];
  isLoading: boolean;
} {
  const { data, isLoading } = useActivityFeed();
  const ctx = useActivityContext(data?.players);
  const chapters = useMemo(
    () =>
      data
        ? buildChronicle(
            { entries: data.entries, players: ctx.players, currentSeq: data.current_seq },
            { systemName: ctx.systemName },
          )
        : [],
    [data, ctx],
  );
  return { chapters, players: ctx.players, isLoading };
}

/**
 * Ile ważnych wpisów Kroniki powstało od ostatniego otwarcia księgi. Pierwsze wczytanie
 * uznaje wszystko za przeczytane (jak `useActivityUnread`); `markSeen` zapisuje stan we
 * wspólnym store, więc przycisk i księga widzą to samo.
 */
export function useChronicleUnread(chapters: ChronicleChapter[]): {
  unread: number;
  markSeen: () => void;
} {
  const latest = useMemo(
    () => Math.max(0, ...chapters.flatMap((c) => c.entries.map((e) => e.seq))),
    [chapters],
  );
  const seen = useChronicleStore((s) => s.seenSeq);
  const setSeen = useChronicleStore((s) => s.markSeen);
  const ready = chapters.length > 0;

  useEffect(() => {
    if (ready && seen === null) setSeen(latest);
  }, [ready, seen, latest, setSeen]);

  const unread =
    seen === null
      ? 0
      : chapters.reduce(
          (sum, c) => sum + c.entries.filter((e) => !e.minor && e.seq > seen).length,
          0,
        );
  return { unread, markSeen: () => setSeen(latest) };
}
