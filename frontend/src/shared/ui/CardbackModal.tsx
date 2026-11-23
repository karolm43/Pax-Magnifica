import { Stack } from "@/ds";
import { ReactNode, useEffect, useState } from "react";
import { useDeckSearchStore } from "@/domains/search/deckSearchStore";
import { useSettingsStore } from "@/state/appStore";
import { Cardback } from "@/shared/ui/Cardback";
import { AppModal } from "@/shared/ui/AppModal";
import styles from "./CardbackModal.module.css";

type CardbackModalProps = {
  imageSrc: string;
  alt: string;
  title: string;
  count?: string | number | ReactNode;
  children: ReactNode;
  modalSize?: string | number;
  cardKey?: string | number;
  /** Talia otwierana z wyszukiwarki planszy (zob. deckSearchStore). */
  deckId?: string;
};

/**
 * A deck's card back. Klik otwiera listę kart talii TYLKO z ustawieniem ``browseDecks``
 * (decyzja użytkownika: w grze nikt nie przegląda talii). Wyszukiwarka planszy nadal otwiera
 * listę - to katalog wszystkich kart puli, nie kolejność ani skład talii w tej grze.
 */
export function CardbackModal({
  imageSrc,
  alt,
  title,
  count = 0,
  children,
  modalSize = 620,
  cardKey,
  deckId,
}: CardbackModalProps) {
  const [opened, setOpened] = useState(false);
  const browse = useSettingsStore((s) => s.settings.browseDecks);
  const request = useDeckSearchStore((state) => state.request);
  useEffect(() => {
    if (deckId && request?.deckId === deckId) setOpened(true);
  }, [deckId, request]);
  const countLine =
    typeof count === "number" || typeof count === "string" ? `${count} in deck` : null;

  return (
    <>
      <Stack
        className={browse ? styles.trigger : undefined}
        onClick={browse ? () => setOpened(true) : undefined}
        title={browse ? undefined : "Deck contents are hidden (Settings → Browse deck contents)"}
      >
        <Cardback key={cardKey} src={imageSrc} alt={alt} count={count} />
      </Stack>
      <AppModal
        opened={opened}
        onClose={() => setOpened(false)}
        size={modalSize}
        title={
          <span className={styles.titleBlock}>
            {title}
            {countLine && <small className={styles.subline}>{countLine}</small>}
          </span>
        }
      >
        {children}
      </AppModal>
    </>
  );
}
