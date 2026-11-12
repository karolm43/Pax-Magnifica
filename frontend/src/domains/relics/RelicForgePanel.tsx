import { useState } from "react";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useForgeOptions } from "@/api/useRelics";
import { fragmentSprite } from "./relicReveal";
import styles from "./RelicForgePanel.module.css";

type Props = {
  playerId: string;
  enabled: boolean;
};

/**
 * Fragmenty gracza i przycisk „Forge relic" (RULES.md 59.7) - w zakładce Relics doku ręki.
 * Silnik liczy, które zestawy są legalne teraz (typ, dżokery Unknown, tura, akcja) i dobiera
 * fragmenty; przycisk tylko je wysyła. Scenę odsłonięcia gra `RelicRevealWatcher` u wszystkich.
 */
export function RelicForgePanel({ playerId, enabled }: Props) {
  const { data: options } = useForgeOptions(playerId, enabled);
  const { forgeRelic } = useBoardEditor();
  const [busy, setBusy] = useState<string | null>(null);

  if (!options?.length) return null;

  return (
    <ul className={styles.panel} aria-label="Relic fragments">
      {options.map((opt) => {
        const ready = opt.reason === null && opt.fragments.length > 0;
        const total = Math.min(opt.owned + opt.wildcards, opt.needed);
        return (
          <li key={opt.kind} className={styles.row} data-ready={ready || undefined}>
            <span className={styles.pips} aria-hidden="true">
              {Array.from({ length: opt.needed }, (_, i) => (
                <img
                  key={i}
                  src={fragmentSprite(i < opt.owned ? "" : "urf1", opt.kind)}
                  alt=""
                  data-missing={i >= total || undefined}
                />
              ))}
            </span>
            <span className={styles.label}>
              <b>
                {opt.owned} {opt.kind}
              </b>
              {opt.wildcards > 0 && <small> + {opt.wildcards} unknown</small>}
            </span>
            <button
              type="button"
              className={styles.forge}
              disabled={!ready || busy !== null}
              title={
                opt.reason ??
                (opt.deckEmpty
                  ? "The relic deck is empty - you purge the fragments without gaining a relic."
                  : `Purge ${opt.needed} fragments to gain 1 relic (uses your action).`)
              }
              onClick={() => {
                setBusy(opt.kind);
                forgeRelic(playerId, opt.fragments)
                  .catch(() => undefined) // powód 422 pokazuje baner (postRaw)
                  .finally(() => setBusy(null));
              }}
            >
              {busy === opt.kind ? "Forging…" : "Forge relic"}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
