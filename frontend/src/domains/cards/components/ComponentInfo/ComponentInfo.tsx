import type { MouseEvent } from "react";
import { IconInfoCircle } from "@tabler/icons-react";
import { ActionCardDetailsCard } from "@/domains/cards/components/ActionCardDetailsCard";
import { BreakthroughCard } from "@/domains/cards/components/BreakthroughCard";
import { LeaderDetailsCard } from "@/domains/cards/components/LeaderDetailsCard";
import { PlanetDetailsCard } from "@/domains/cards/components/PlanetDetailsCard";
import { PromissoryNoteCard } from "@/domains/cards/components/PromissoryNoteCard";
import { SecretObjectiveCard } from "@/domains/cards/components/SecretObjectiveCard";
import { StrategyCardDetailsCard } from "@/domains/cards/components/StrategyCardDetailsCard";
import { TechCard } from "@/domains/cards/components/TechCard/TechCard";
import { RelicCard } from "@/domains/player/components/Relic/RelicCard";
import { hintFor, type NamedKind } from "@/domains/game-shell/components/ActivityPanel/Named";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { useDisclosure } from "@/hooks/useDisclosure";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { useGameData } from "@/state/useGameContext";
import styles from "./ComponentInfo.module.css";

/*
 * Jeden sposób na „co to jest?” w oknach decyzji: odnośnik do komponentu gry (karta strategii,
 * relikt, technologia, przełom, agenda, cel, karta akcji, notka, lider, planeta, eksploracja)
 * => pełna karta - ta sama, którą pokazuje panel gracza po kliknięciu chipu.
 */

export type ComponentKind = Exclude<NamedKind, "system">;

export type ComponentRef = { kind: ComponentKind; id: string };

const KINDS = new Set<string>([
  "actionCard",
  "agenda",
  "explore",
  "tech",
  "objective",
  "strategy",
  "planet",
  "leader",
  "promissory",
  "relic",
  "breakthrough",
]);

/** Odnośnik z ``meta.ref`` opcji silnika (``offer_inputs.option(ref=...)``) albo ``null``. */
export function refFromMeta(meta: Record<string, unknown> | undefined): ComponentRef | null {
  const ref = meta?.ref;
  if (!ref || typeof ref !== "object") return null;
  const { kind, id } = ref as { kind?: unknown; id?: unknown };
  if (typeof kind !== "string" || !KINDS.has(kind) || typeof id !== "string" || !id) return null;
  return { kind: kind as ComponentKind, id };
}

/** Karta zastępcza: nazwa, rodzaj i pełny tekst z ``hintFor`` (agendy, cele publiczne, eksploracja). */
function HintCard({ componentRef }: { componentRef: ComponentRef }) {
  const gameData = useGameData();
  const hint = hintFor(componentRef.kind, componentRef.id, { idMap: gameData?.strategyCardIdMap });
  if (!hint) return null;
  return (
    <DetailsCard width={340} color="purple">
      <DetailsCard.Title title={hint.name} type={hint.meta} />
      {hint.lines.map((line, index) => (
        <DetailsCard.Section key={index} content={line} />
      ))}
    </DetailsCard>
  );
}

/** Pełna karta komponentu (jak w panelu gracza / na stole). */
export function ComponentCard({ componentRef }: { componentRef: ComponentRef }) {
  const { kind, id } = componentRef;
  switch (kind) {
    case "strategy":
      return <StrategyCardDetailsCard initiative={Number(id)} />;
    case "relic":
      return <RelicCard relicId={id} />;
    case "tech":
      return <TechCard techId={id} />;
    case "breakthrough":
      return <BreakthroughCard breakthroughId={id} />;
    case "actionCard":
      return <ActionCardDetailsCard actionCardId={id} />;
    case "leader":
      return <LeaderDetailsCard leaderId={id} />;
    case "promissory":
      return <PromissoryNoteCard promissoryNoteId={id} />;
    case "planet":
      return <PlanetDetailsCard planetId={id} />;
    case "objective":
      return getSecretObjectiveData(id) ? (
        <SecretObjectiveCard secretId={id} />
      ) : (
        <HintCard componentRef={componentRef} />
      );
    default:
      return <HintCard componentRef={componentRef} />;
  }
}

/**
 * Przycisk ⓘ: klik otwiera pełną kartę komponentu (nie wybiera opcji - klik nie przechodzi
 * do kafelka pod spodem). Działa też na dotyku, w przeciwieństwie do dymka po najechaniu.
 */
export function ComponentInfoButton({
  componentRef,
  name,
  className,
}: {
  componentRef: ComponentRef;
  /** Nazwa do etykiety dostępności („About Leadership”). */
  name: string;
  className?: string;
}) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const onClick = (event: MouseEvent) => {
    event.stopPropagation();
    event.preventDefault();
    toggle();
  };
  return (
    <SmoothPopover opened={opened} onChange={setOpened} position="right">
      <SmoothPopover.Target>
        <button
          type="button"
          className={className ?? styles.info}
          aria-label={`About ${name}`}
          aria-expanded={opened}
          title="Click for the full card"
          onClick={onClick}
        >
          <IconInfoCircle size={14} aria-hidden="true" />
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <ComponentCard componentRef={componentRef} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
