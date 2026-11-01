import { useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import type { TopicContent, TopicGroupKey } from "@/domains/rules/types";

/*
 * Router reguł żyje w KORZENIU backendu pod prefiksem /rules. Proxy Vite mapuje
 * "/bot/<x>" -> "/<x>" na backendzie, więc bazą jest samo "/bot" (por.
 * useRulesIndex.ts oraz useNewGame.ts).
 */
const BOT_ROOT = "/bot";

/**
 * Surowy kształt treści tematu na drucie — lustro `TopicContentDTO` backendu.
 *
 * Backend serializuje pole `is_empty_note` w snake_case; model frontu
 * (`TopicContent`) używa `isEmptyNote` w camelCase. Mapowanie wykonujemy w
 * `queryFn` poniżej, tuż po pobraniu surowego DTO.
 */
type TopicContentRaw = {
  slug: string;
  title: string;
  group: TopicGroupKey;
  markdown: string;
  is_empty_note: boolean;
};

/** Mapuje surowe DTO (snake_case) na model frontu (camelCase). */
function toTopicContent(raw: TopicContentRaw): TopicContent {
  return {
    slug: raw.slug,
    title: raw.title,
    group: raw.group,
    markdown: raw.markdown,
    isEmptyNote: raw.is_empty_note,
  };
}

/**
 * Pobiera treść pojedynczego tematu (GET /bot/rules/:slug -> /rules/:slug).
 *
 * Treść jest statyczna (plik Markdown na dysku), więc `staleTime: Infinity`.
 * Zapytanie uruchamia się wyłącznie, gdy podano `slug` (`enabled`), aby nie
 * strzelać do backendu bez wybranego tematu.
 */
export function useTopicContent(slug: string | null | undefined) {
  return useQuery<TopicContent>({
    queryKey: ["rules", "topic", slug],
    queryFn: async () => {
      const raw = await fetchJson<TopicContentRaw>(
        `${BOT_ROOT}/rules/${slug}`,
        "rules topic",
      );
      return toTopicContent(raw);
    },
    enabled: Boolean(slug),
    staleTime: Infinity,
  });
}
