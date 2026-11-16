import { useEffect, useRef, useState, type CSSProperties } from "react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getTokenImagePath, getTokenScale } from "@/entities/lookup/tokens";
import { getAttachmentImagePath } from "@/entities/lookup/attachments";
import { getTokenSprite } from "@/shared/ui/Token/tokenSprites";
import { getRenderedStackFootprint } from "@/entities/geometry/renderedStackGeometry";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { getTokenRule } from "./SystemDossier/featureRules";
import { PositionedSprite } from "./PositionedSprite";
import { forwardClickBelow } from "./forwardClickBelow";
import {
  linkKindsOfToken,
  useWormholeHoverStore,
  type WormholeHover,
} from "../wormholeLinks";

type TokenProps = {
  tokenId: string;
  faction?: string;
  x: number;
  y: number;
  zIndex: number;
  /** Pozycja systemu — dla podglądu „dokąd prowadzi” wormhole / ingress. */
  tilePosition?: string;
};

/** Opóźnienie dymka po najechaniu — jak przy planetach, ale krócej (żeton jest mały). */
const HOVER_DELAY_MS = 500;

export const Token = ({ tokenId, faction, x, y, zIndex, tilePosition }: TokenProps) => {
  const alt = `${faction || "token"} ${tokenId}`;
  const tokenImagePath = getTokenImagePath(tokenId);
  const imagePath = tokenImagePath || getAttachmentImagePath(tokenId);
  if (!imagePath) return null;

  /* The large DMZ token renders at its footprint size to keep it in place. */
  if (tokenId === "dmz_large") {
    const footprint = getRenderedStackFootprint({
      entityId: tokenId,
      entityType: "token",
      count: 1,
    });
    return (
      <img
        src={assetUrl(imagePath)}
        alt={alt}
        style={{
          width: `${footprint.width}px`,
          height: `${footprint.height}px`,
          position: "absolute",
          left: `${x}px`,
          top: `${y}px`,
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
        }}
      />
    );
  }

  const scale = getTokenScale(tokenId);
  const sprite = getTokenSprite(tokenImagePath ? "token" : "attachment", tokenId);
  const transform =
    scale !== 1
      ? `translate(-50%, -50%) scale(${scale})`
      : "translate(-50%, -50%)";

  const rule = getTokenRule(tokenId);
  if (!rule || !sprite) {
    return (
      <PositionedSprite
        sprite={sprite}
        imagePath={imagePath}
        alt={alt}
        style={{
          position: "absolute",
          left: `${x}px`,
          top: `${y}px`,
          transform,
          zIndex,
        }}
      />
    );
  }

  // Żeton z opisem reguły: ramka o rozmiarze PO skalowaniu jest celem dymka
  // (najechanie z opóźnieniem albo kliknięcie), a sprite stoi w jej środku.
  const width = sprite.width * scale;
  const height = sprite.height * scale;
  return (
    <TokenWithInfo
      rule={rule}
      link={
        tilePosition && linkKindsOfToken(tokenId).length > 0
          ? { position: tilePosition, kinds: linkKindsOfToken(tokenId) }
          : undefined
      }
      imagePath={imagePath}
      frameStyle={{
        position: "absolute",
        left: `${x}px`,
        top: `${y}px`,
        width: `${width}px`,
        height: `${height}px`,
        transform: "translate(-50%, -50%)",
        zIndex,
      }}
    >
      <PositionedSprite
        sprite={sprite}
        imagePath={imagePath}
        alt={alt}
        style={{
          position: "absolute",
          left: `${width / 2}px`,
          top: `${height / 2}px`,
          transform,
        }}
      />
    </TokenWithInfo>
  );
};

function TokenWithInfo({
  rule,
  link,
  imagePath,
  frameStyle,
  children,
}: {
  rule: { name: string; rule: string };
  link?: WormholeHover;
  imagePath: string;
  frameStyle: CSSProperties;
  children: React.ReactNode;
}) {
  const [opened, setOpened] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const setHovered = useWormholeHoverStore((st) => st.setHovered);
  const clearHovered = useWormholeHoverStore((st) => st.clearHovered);
  // Linie zostają tylko dopóki kursor stoi na żetonie; odmontowanie też je gasi.
  const linkPosition = link?.position;
  useEffect(
    () => (linkPosition ? () => clearHovered(linkPosition) : undefined),
    [linkPosition, clearHovered],
  );

  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        <span
          role="button"
          tabIndex={0}
          aria-label={rule.name}
          style={{ ...frameStyle, pointerEvents: "auto" }}
          onMouseEnter={() => {
            if (link) setHovered(link);
            window.clearTimeout(timer.current);
            timer.current = window.setTimeout(() => setOpened(true), HOVER_DELAY_MS);
          }}
          onMouseLeave={() => {
            if (link) clearHovered(link.position);
            window.clearTimeout(timer.current);
            setOpened(false);
          }}
          // Żeton (np. Custodians na Mecatol Rex) nie może blokować klikania w system.
          // Klik jest PRZEKAZYWANY elementowi pod żetonem (cel heksa: zaznaczenie /
          // aktywacja systemu). Prawy klik bąbelkuje do menu kafelka („Activate
          // system"). Opis reguły: najechanie z opóźnieniem.
          onClick={forwardClickBelow}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setOpened((o) => !o);
            }
          }}
        >
          {children}
        </span>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <DetailsCard width={320}>
          <DetailsCard.Title
            title={rule.name}
            type="Map token"
            icon={
              <DetailsCard.Icon
                shape="round"
                icon={
                  <img
                    src={assetUrl(imagePath)}
                    alt=""
                    style={{ width: 30, height: 30, objectFit: "contain" }}
                  />
                }
              />
            }
          />
          <DetailsCard.Section title="Rule" content={rule.rule} />
        </DetailsCard>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
