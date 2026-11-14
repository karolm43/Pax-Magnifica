import { assetUrl } from "@/shared/assets/resolveAsset";
import { getAttachmentData } from "@/entities/lookup/attachments";
import styles from "./PlanetCard.module.css";

function describe(attachmentId: string): string {
  const data = getAttachmentData(attachmentId);
  if (!data) return attachmentId;
  const mods = [
    data.resourcesModifier ? `+${data.resourcesModifier} resources` : null,
    data.influenceModifier ? `+${data.influenceModifier} influence` : null,
    data.techSpeciality?.length
      ? `${data.techSpeciality.join(", ").toLowerCase()} skip`
      : null,
  ].filter(Boolean);
  return mods.length > 0 ? `${data.name || attachmentId} (${mods.join(", ")})` : data.name || attachmentId;
}

/**
 * Żetony attachmentów planety pod kartą — w panelach wydawania (tryb wyboru), gdzie klik
 * wybiera planetę zamiast otwierać szczegóły, więc attachment musi być widać od razu.
 * Ten sam asset co w szczegółach planety (`PlanetDetailsCard`).
 */
export function PlanetAttachmentStrip({ attachments }: { attachments: string[] }) {
  if (attachments.length === 0) return null;
  const label = attachments.map(describe).join(" · ");
  return (
    <span className={styles.attachmentStrip} role="img" aria-label={`Attachments: ${label}`} title={label}>
      {attachments.map((id, index) => {
        const data = getAttachmentData(id);
        return data ? (
          <img
            key={`${id}-${index}`}
            src={assetUrl(`/attachment_token/${data.imagePath}`)}
            alt=""
          />
        ) : null;
      })}
    </span>
  );
}
