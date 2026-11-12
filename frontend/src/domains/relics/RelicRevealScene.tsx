import type { CSSProperties } from "react";
import type { RelicReveal } from "@/entities/data/types";
import { getRelicData } from "@/entities/lookup/relics";
import { assetUrl } from "@/shared/assets/resolveAsset";
import {
  RELIC_BACK,
  relicFaceImage,
  revealFragments,
  revealHeadline,
} from "./relicReveal";
import styles from "./RelicReveal.module.css";

type Props = {
  reveal: RelicReveal;
  /** Nazwa gracza (frakcji) i jego kolor jako składowe `r g b`. */
  who: string;
  rgb: string;
  names: { planet?: string; card?: string };
  onClose: () => void;
};

/** Iskry wokół sceny - rozkład deterministyczny (bez losowania przy każdym renderze). */
const SPARKS = Array.from({ length: 18 }, (_, i) => ({
  x: ((i * 37) % 100) - 50,
  delay: (i % 6) * 0.22,
  size: 3 + (i % 3) * 2,
}));

/**
 * Scena odsłonięcia reliktu (RULES.md 59.8), widoczna dla wszystkich graczy:
 * - `fragments`: trzy fragmenty krążą, zlewają się w błysku w kartę reliktu;
 * - `fracture`: pęknięcie w przestrzeni rozdziera się i wypuszcza kartę;
 * - pozostałe (`explore`, `deck`): karta spływa z góry.
 * Karta obraca się awersem: dziś placeholder (rewers + nazwa), docelowo grafika karty.
 */
export function RelicRevealScene({ reveal, who, rgb, names, onClose }: Props) {
  const relic = reveal.relicId ? getRelicData(reveal.relicId) : undefined;
  const relicName = relic?.name ?? reveal.relicId ?? "";
  const face = reveal.relicId ? relicFaceImage(reveal.relicId) : null;
  const back = assetUrl(RELIC_BACK);
  const { title, subtitle } = revealHeadline(reveal, who, names);
  const empty = reveal.relicId === null;
  const paragraphs = (relic?.text ?? "").split("\n").filter(Boolean);

  return (
    <div
      className={styles.stage}
      data-source={reveal.source}
      data-empty={empty || undefined}
      style={{ "--who": rgb } as CSSProperties}
      role="dialog"
      aria-modal="true"
      aria-label={empty ? title : `Relic revealed: ${relicName}`}
    >
      <div className={styles.backdrop} aria-hidden="true" />

      <header className={styles.header}>
        <span className={styles.kicker}>{subtitle}</span>
        <h2 className={styles.title}>{title}</h2>
      </header>

      <div className={styles.hero}>
      <div className={styles.center} aria-hidden="true">
        {reveal.source === "fragments" && (
          <div className={styles.orbit}>
            {revealFragments(reveal).map((src, i, all) => (
              <img
                key={i}
                className={styles.fragment}
                src={src}
                alt=""
                style={{ "--a": `${(360 / all.length) * i - 90}deg` } as CSSProperties}
              />
            ))}
          </div>
        )}
        {reveal.source === "fracture" && (
          <>
            <svg className={styles.crack} viewBox="0 0 600 120" preserveAspectRatio="none">
              <path
                pathLength={1}
                d="M0 60 L70 52 L110 68 L170 44 L215 72 L260 50 L300 64 L345 40 L390 70 L440 48 L490 66 L540 50 L600 58"
              />
            </svg>
            <div className={styles.beam} />
          </>
        )}
        <div className={styles.flash} />
        <div className={styles.ring} />
        {SPARKS.map((s, i) => (
          <span
            key={i}
            className={styles.spark}
            style={
              {
                "--x": `${s.x * 6}px`,
                "--d": `${s.delay}s`,
                "--s": `${s.size}px`,
              } as CSSProperties
            }
          />
        ))}
      </div>

      {!empty && (
        <div className={styles.cardWrap}>
          <div className={styles.card}>
            <div className={styles.cardBack} style={{ backgroundImage: `url("${back}")` }} />
            <div className={styles.cardFace}>
              {face ? (
                <img src={face} alt={relicName} />
              ) : (
                <div
                  className={styles.placeholder}
                  style={{ backgroundImage: `url("${back}")` }}
                >
                  <span className={styles.placeholderKind}>Relic</span>
                  <span className={styles.placeholderName}>{relicName}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      </div>

      <section className={styles.info}>
        {empty ? (
          <p className={styles.effect}>The relic deck is empty - no relic was gained.</p>
        ) : (
          <>
            <h3 className={styles.relicName}>{relicName}</h3>
            {paragraphs.map((line, i) => (
              <p key={i} className={styles.effect}>
                {line}
              </p>
            ))}
            {relic?.flavourText && <p className={styles.flavour}>{relic.flavourText}</p>}
          </>
        )}
        <button type="button" className={styles.ok} onClick={onClose} autoFocus>
          OK
        </button>
      </section>
    </div>
  );
}
