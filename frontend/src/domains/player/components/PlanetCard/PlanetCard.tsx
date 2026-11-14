import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from "react";
import { Stack, Box, Text } from "@/ds";
import cx from "clsx";
import { PlanetAbilityCard } from "../PlanetAbilityCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { PlanetDetailsCard } from "@/domains/cards/components/PlanetDetailsCard";
import styles from "./PlanetCard.module.css";
import { PlanetAttachmentStrip } from "./PlanetAttachmentStrip";
import { getPlanetData } from "@/entities/lookup/planets";
import { usePlanet } from "@/hooks/usePlanet";
import type { Planet } from "@/entities/data/types";
import { useAppStore } from "@/state/appStore";
import { useDisclosure } from "@/hooks/useDisclosure";
import { mergePlanetTraits } from "@/entities/game/planetTraits";
import { isMobileDevice } from "@/utils/isTouchDevice";
import { getPlanetTileBackground } from "./planetTileBackground";
import { lowPriorityImageProps } from "@/shared/ui/imageLoading";
import { getAttachmentModifiers } from "@/entities/game/planets";
import { searchKey, searchTarget } from "@/domains/search/searchKeys";
import {
  calculateFinalValues,
  createIconSources,
  getCSSVariables,
  getPlanetIconSrc,
  getPlanetIconStyle,
  getStackedIconStyle,
  isOceanicPlanet,
  planetCssType,
} from "./planetCardStyle";

type Props = {
  planetId: string;
  legendaryAbilityExhausted?: boolean;
  /** Overrides the exhausted state read from the map tile. */
  isExhausted?: boolean;
  /** Tryb wyboru (np. płatność w produkcji): klik woła to zamiast otwierać kartę szczegółów. */
  onPick?: () => void;
  /** Zaznaczenie w trybie wyboru (złota ramka). */
  picked?: boolean;
  /** Właściciel — przyjmowany dla zgodności; menu prawego klawisza usunięte (stan obsługuje gra). */
  playerId?: string;
};

function PlanetCompactValues({
  iconSources,
  resources,
  influence,
}: {
  iconSources: string[];
  resources: number;
  influence: number;
}) {
  return (
    <Box className={styles.planetValues}>
      {iconSources.length > 0 && (
        <Box
          className={styles.iconsStack}
          style={getStackedIconStyle(iconSources)}
        />
      )}
      <span className={cx(styles.planetValue, styles.resourceValue)}>
        {resources}
      </span>
      <span className={cx(styles.planetValue, styles.influenceValue)}>
        {influence}
      </span>
    </Box>
  );
}

function PlanetDecorations({ planetData }: { planetData: Planet }) {
  const tileBackground = isMobileDevice()
    ? null
    : getPlanetTileBackground(planetData);

  return (
    <>
      {tileBackground && (
        <Box
          className={styles.tileArtMask}
          style={tileBackground.maskStyle}
          aria-hidden="true"
        >
          <img
            {...lowPriorityImageProps}
            className={styles.tileArtImage}
            src={tileBackground.src}
            alt=""
            style={tileBackground.imageStyle}
          />
        </Box>
      )}
    </>
  );
}

export function PlanetCard({
  planetId,
  legendaryAbilityExhausted = false,
  isExhausted: isExhaustedProp,
  onPick,
  picked = false,
}: Props) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const planetData = getPlanetData(planetId);
  const planetTile = usePlanet(planetId);
  const setHoveredPlanetId = useAppStore((state) => state.setHoveredPlanetId);
  const setScrollToPlanetId = useAppStore((state) => state.setScrollToPlanetId);

  if (!planetData) return null;

  const isExhausted = isExhaustedProp ?? planetTile?.exhausted ?? false;

  const attachments = planetTile?.attachments ?? [];
  const attachmentModifiers = getAttachmentModifiers(
    attachments,
    planetData.techSpecialties ?? [],
  );
  const finalTraits = mergePlanetTraits(
    planetData.planetTypes ||
      (planetData.planetType ? [planetData.planetType] : []),
    attachmentModifiers.planetTypes,
  );
  const { finalResources, finalInfluence } = calculateFinalValues(
    planetData,
    attachmentModifiers,
    planetTile,
  );
  const isLegendary =
    !!planetData.legendaryAbilityText || attachments.includes("nanoforge");
  const { legendaryAbilityName, legendaryAbilityText } = planetData;
  const hasLegendaryAbility = !!(legendaryAbilityName && legendaryAbilityText);
  const isOceanic = isOceanicPlanet(planetId, planetData);
  const cssVariables = getCSSVariables(planetCssType(isOceanic, finalTraits));
  const planetIconSrc = getPlanetIconSrc(planetData, finalTraits);
  const searchAttributes = searchTarget(searchKey("planet", planetId));

  const planetCardContent = (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        <Stack
          onClick={() => {
            if (onPick) {
              onPick();
              return;
            }
            toggle();
            setScrollToPlanetId(planetId);
          }}
          role={onPick ? "button" : undefined}
          tabIndex={onPick ? 0 : undefined}
          aria-pressed={onPick ? picked : undefined}
          onKeyDown={
            onPick
              ? (event: ReactKeyboardEvent) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onPick();
                  }
                }
              : undefined
          }
          onMouseEnter={() => setHoveredPlanetId(planetId)}
          onMouseLeave={() => setHoveredPlanetId(null)}
          {...(!hasLegendaryAbility && searchAttributes)}
          className={cx(
            styles.mainStack,
            isLegendary && styles.legendary,
            hasLegendaryAbility && styles.noRightRadius,
            isExhausted && styles.exhausted,
            planetIconSrc && styles.hasPlanetIcon,
            picked && styles.picked,
          )}
          style={{ ...cssVariables, ...getPlanetIconStyle(planetIconSrc) }}
        >
          <PlanetDecorations planetData={planetData} />
          {attachments.length > 0 && (
            <span
              className={styles.attachmentCorner}
              role="img"
              aria-label="Has attachments"
              title="Has attachments"
            />
          )}
          <Text className={styles.planetName}>
            {planetData.shortName ?? planetData.name}
          </Text>
          <PlanetCompactValues
            iconSources={createIconSources(planetData, attachmentModifiers)}
            resources={finalResources}
            influence={finalInfluence}
          />
        </Stack>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown className={styles.popoverDropdown}>
        <PlanetDetailsCard planetId={planetId} planetTile={planetTile} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );

  // Panele wydawania (tryb wyboru): attachmenty widoczne pod kartą, bo klik nie otwiera szczegółów.
  const withAttachments = (content: ReactNode) =>
    onPick && attachments.length > 0 ? (
      <div className={styles.pickColumn}>
        {content}
        <PlanetAttachmentStrip attachments={attachments} />
      </div>
    ) : (
      content
    );

  if (!legendaryAbilityName || !legendaryAbilityText) {
    return withAttachments(
      <>
        {planetCardContent}
      </>,
    );
  }

  return withAttachments(
    <div
      className={cx(styles.legendaryWrapper, isExhausted && styles.wrapperExhausted)}
      style={cssVariables}
      {...searchAttributes}
      onClick={() => setScrollToPlanetId(planetId)}
      onMouseEnter={() => setHoveredPlanetId(planetId)}
      onMouseLeave={() => setHoveredPlanetId(null)}
    >
      {planetCardContent}
      <PlanetAbilityCard
        planetId={planetId}
        abilityName={legendaryAbilityName}
        abilityText={legendaryAbilityText}
        actionCards={planetTile?.actionCards}
        exhausted={legendaryAbilityExhausted}
        joinedRight
      />
    </div>,
  );
}
