/**
 * Model TypeScript przeglądarki Zasad (Rules_Browser) — lustro DTO backendu.
 *
 * Odpowiada DTO z `src/api/schemas.py` oraz modelom core z
 * `src/core/rules_content.py`. Różnica nazewnicza: backend serializuje pole
 * `is_empty_note` (snake_case) na drucie, a model frontu używa `isEmptyNote`
 * (camelCase) — mapowanie z surowego DTO na ten typ wykonuje hook danych
 * (`useTopicContent`, zadanie 8.2), nie ten plik.
 */

/** Klucz grupy tematu: Reguły / Frakcje / Komponenty (prefiks pliku R_/F_/C_). */
export type TopicGroupKey = "rules" | "factions" | "components";

/**
 * Pojedyncza pozycja indeksu tematów (Topic_Index).
 * - `slug`: Topic_Slug — nazwa pliku bez `.md` (np. `R_movement`).
 * - `title`: tytuł z pierwszego nagłówka `# ` albo slug jako fallback.
 * - `group`: klucz grupy wynikający z prefiksu slug.
 */
export type TopicIndexEntry = {
  slug: string;
  title: string;
  group: TopicGroupKey;
};

/**
 * Grupa tematów w indeksie (Reguły / Frakcje / Komponenty).
 * - `label`: etykieta po polsku ("Reguły" | "Frakcje" | "Komponenty").
 * - `entries`: pozycje należące do grupy w deterministycznej kolejności.
 */
export type TopicGroup = {
  group: TopicGroupKey;
  label: string;
  entries: TopicIndexEntry[];
};

/**
 * Pełny indeks tematów — grupy w stałej kolejności Reguły → Frakcje → Komponenty.
 */
export type RulesIndex = {
  groups: TopicGroup[];
};

/**
 * Treść pojedynczego tematu gotowa do renderowania na froncie.
 * - `markdown`: surowa treść pliku `.md` do renderowania klient-side.
 * - `isEmptyNote`: `true` dla tematu F/C bez not poza nagłówkiem i blockquote
 *   źródła (zawsze `false` dla grupy Reguły). Mapowane z DTO `is_empty_note`.
 */
export type TopicContent = {
  slug: string;
  title: string;
  group: TopicGroupKey;
  markdown: string;
  isEmptyNote: boolean;
};

/**
 * Wynik Link_Mapper — cel hiperłącza z treści tematu.
 * Internal_Link wskazuje lokalny temat (`slug`); External_Link zachowuje
 * oryginalny adres (`url`).
 */
export type LinkTarget =
  | { kind: "internal"; slug: string }
  | { kind: "external"; url: string };
