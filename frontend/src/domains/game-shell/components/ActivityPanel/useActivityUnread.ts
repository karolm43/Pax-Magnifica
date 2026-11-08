import { useEffect, useState } from "react";
import { useActivityFeed } from "@/api/useBoardEditor";

/**
 * Ile nowych wpisów feedu pojawiło się od ostatniego otwarcia panelu.
 * Wpisy God-Mode nie liczą się jako powiadomienia. Przy pierwszym załadowaniu
 * feedu wszystko uznajemy za przeczytane (brak „fali" starych powiadomień).
 */
export function useActivityUnread(open: boolean): number {
  const { data } = useActivityFeed();
  const [seenSeq, setSeenSeq] = useState<number | null>(null);

  const latest = data?.entries.at(-1)?.seq ?? 0;

  useEffect(() => {
    if (!data) return;
    if (seenSeq === null || open) setSeenSeq(latest);
  }, [data, latest, open, seenSeq]);

  if (!data || seenSeq === null) return 0;
  return data.entries.filter(
    (e) => e.seq > seenSeq && e.activity.kind !== "godmode",
  ).length;
}
