import { useState, type ReactElement } from "react";
import { useParams } from "react-router-dom";
import { useGameState } from "@/api/useGameState";
import { useBoardEditor, useStrategyCards } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import { getStrategyCardByInitiative } from "@/entities/lookup/strategyCards";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import { playerNameForColor } from "../gameStatePlayers";
import { DEFAULT_GAME_ID } from "@/config";
import type { PlayerData } from "@/entities/data/types";
import styles from "./StrategyCardTable.module.css";

/* Initiative → sygnał koloru dysku (spójnie z pickerem w GameStatePanel). */
const SC_TONE: Record<number, string> = {
  1: "var(--gd-red)",
  2: "var(--gd-orange)",
  3: "var(--gd-yellow)",
  4: "var(--gd-green)",
  5: "var(--gd-teal)",
  6: "var(--gd-cyan)",
  7: "var(--gd-blue)",
  8: "var(--gd-purple)",
};

/**
 * Znacznik frakcji właściciela karty — ten sam wzorzec, co ``FactionMark`` w
 * ``GameStatePanel`` (``CircularFactionIcon`` z override'ami obrazka). Gdy gracz nie
 * ma ustawionej frakcji, rezerwuje miejsce o zadanym rozmiarze (brak skakania layoutu).
 */
function FactionMark({
  player,
  size,
}: {
  player: PlayerData | undefined;
  size: number;
}): ReactElement {
  if (!player?.faction) return <span style={{ width: size, height: size }} />;
  return (
    <CircularFactionIcon
      faction={player.faction}
      size={size}
      factionImageOverride={player.factionImage}
      factionImageTypeOverride={player.factionImageType}
    />
  );
}

/**
 * Card_Table_View (Requirement 1, 8) — widok kart strategii „na stole" w stylu
 * AsyncTI4, montowany jako nakładka nad mapą OBOK istniejącego ``GameStatePanel``
 * (który ZOSTAJE jako alternatywny picker, Requirement 8.2). Oba czytają ten sam
 * ``gameData``/``useStrategyCards``, więc odzwierciedlają ten sam stan gry.
 *
 * RENDER (zadanie 9.2): pełna grafika kart (``ti4ultimate.com`` przez
 * ``getStrategyCardByInitiative(...).imageURL``), oznaczenie wybranych kart i ich
 * właściciela, wyróżnienie aktualnego pickera oraz nagłówek z mówcą i komunikatami
 * stanu (R1.4/R1.5). Fallback tekstowy przy braku/błędzie grafiki (R8.8).
 *
 * INTERAKCJA (zadanie 9.3): każda karta to klikalny ``<button>``. Klik WOLNEJ karty,
 * gdy jest wskazany picker → ``pickStrategyCard(pickerId, card.initiative)`` (R8.5).
 * Karta wybrana albo brak pickera / nie twoja kolej → blokada przez ``disabled`` +
 * strażnik ``canPick`` (jak w istniejącym pickerze): klik NIE wysyła requestu (R8.6).
 *
 * Źródła danych: WYŁĄCZNIE istniejące hooki (zero nowych):
 * - ``useGameState`` → ``gameState`` (faza, mówca, aktywny gracz) — ten sam
 *   selektor web-data, którego używa ``GameStatePanel`` (spójny stan, R8.2);
 * - ``useStrategyCards`` → pula kart zestawu + ich stan (``StrategyCardState[]``);
 * - ``useGameData`` → ``playerData`` (właściciel → ``FactionMark``/kolor) oraz
 *   ``strategyCardIdMap`` (lookup grafiki pełnej karty);
 * - ``useBoardEditor`` → akcja ``pickStrategyCard`` (wybór karty dla pickera).
 */
export function StrategyCardTable(): ReactElement | null {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: cards } = useStrategyCards();
  const gameData = useGameData();
  // Akcja wyboru karty — ta sama, której używa ``StrategyCardPicker`` w
  // ``GameStatePanel`` (identyczny kontrakt: ``pickStrategyCard(discordId, initiative)``).
  const { pickStrategyCard } = useBoardEditor();

  // Karty, których grafika nie wczytała się (``onError``) — przełączamy je na
  // fallback tekstowy (R8.8). Klucz = initiative.
  const [failedImages, setFailedImages] = useState<Record<number, boolean>>({});

  // Blokada podwójnego requestu w trakcie trwającego wyboru — ten sam wzorzec
  // ``busy``/``run``, co w ``StrategyCardPicker`` (GameStatePanel). Zapobiega
  // wysłaniu kolejnego ``pickStrategyCard`` zanim poprzedni się rozstrzygnie.
  const [busy, setBusy] = useState(false);

  // Gating fazy: render tylko w fazie strategii (Requirement 8.1). Poza nią —
  // komponent nie istnieje w drzewie (zwraca ``null``), więc nie dubluje się z
  // innymi nakładkami i nie wpływa na pozostałe fazy.
  if (gameState?.phase !== "strategy") return null;
  if (!cards || cards.length === 0) return null;

  const players = gameData?.playerData ?? [];

  // Opakowanie akcji wyboru — serializuje requesty przez flagę ``busy`` (tak jak
  // ``run`` w ``StrategyCardPicker``): kolejny klik jest ignorowany, dopóki
  // poprzedni ``pickStrategyCard`` się nie zakończy.
  const run = async (fn: () => Promise<void>): Promise<void> => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  // Picker = gracz, którego ``color === gameState.activePlayer`` w fazie strategii
  // (spójnie ze ``StrategyCardPicker`` w GameStatePanel; R8.9). ``null``, gdy nikt
  // nie jest wskazany (brak kolejki / wszyscy wybrali).
  const pickerColor = gameState.activePlayer;
  // Gracz-picker i jego IDENTYFIKATOR do wywołania akcji. ``pickStrategyCard``
  // oczekuje ``discordId`` (DOKŁADNIE ten sam identyfikator, co istniejący picker:
  // ``pickStrategyCard(picker.player.discordId, ...)``), więc mapujemy kolor
  // aktywnego gracza na jego ``discordId``.
  const pickerPlayer = pickerColor
    ? players.find((p) => p.color === pickerColor)
    : undefined;
  const pickerId = pickerPlayer?.discordId ?? null;

  // Mówca: ``gameState.speaker`` to KOLOR — mapujemy na nazwę gracza (R1.4).
  const speakerColor = gameState.speaker ?? null;
  const speakerName = speakerColor
    ? playerNameForColor(players, speakerColor)
    : null;

  // Nazwa aktualnego pickera do podnagłówka (R1.5). Gdy picker nieznany, pokazujemy
  // komunikat „brak gracza do wskazania".
  const pickerName = pickerColor
    ? playerNameForColor(players, pickerColor)
    : null;

  return (
    <div className={styles.table} aria-label="Karty strategii na stole">
      {/* Nagłówek fazy + mówca + aktualny picker (Requirement 1). */}
      <div className={styles.header}>
        <span className={styles.heading}>Faza strategii</span>
        <span className={styles.speaker}>
          {speakerName ? (
            <>
              Mówca:{" "}
              <b className={styles.speakerName}>{speakerName}</b>
            </>
          ) : (
            "brak ustawionego mówcy"
          )}
        </span>
        <span className={styles.picker}>
          {pickerName ? (
            <>
              Wybiera:{" "}
              <b className={styles.pickerName}>{pickerName}</b>
            </>
          ) : (
            "brak gracza do wskazania"
          )}
        </span>
      </div>

      <div className={styles.cards} role="list">
        {cards.map((card) => {
          // Pełna grafika karty z realnego źródła (``ti4ultimate.com``) przez
          // istniejący lookup (R8.1, R8.3). Fallback tekstowy, gdy brak URL lub
          // obrazek się nie wczytał (R8.8).
          const def = getStrategyCardByInitiative(
            card.initiative,
            gameData?.strategyCardIdMap,
          );
          const imageURL = def?.imageURL;
          const showImage = !!imageURL && !failedImages[card.initiative];
          const name = card.name || SC_NAMES[card.initiative] || "—";

          // Właściciel = gracz, który wybrał kartę (``picked_by`` to discordId).
          const owner = card.picked_by
            ? players.find((p) => p.discordId === card.picked_by)
            : undefined;
          const isPicked = card.picked_by != null;

          // ``canPick`` — ten sam strażnik, co w istniejącym pickerze
          // (``!owner && !!picker``): karta WOLNA (``picked_by == null``) ORAZ jest
          // wskazany picker (``activePlayer != null`` → mamy ``pickerId``). Gdy
          // ``false``: karta wybrana albo brak pickera / nie twoja kolej (R8.6) —
          // klik nie wysyła requestu (``disabled`` + strażnik w ``onClick``).
          const canPick = !isPicked && pickerId !== null;

          return (
            <button
              key={card.initiative}
              type="button"
              role="listitem"
              className={styles.card}
              data-picked={isPicked || undefined}
              disabled={busy || !canPick}
              aria-disabled={!canPick || undefined}
              style={{ ["--scc" as string]: SC_TONE[card.initiative] }}
              title={
                isPicked
                  ? `Wybrana: ${
                      owner
                        ? playerNameForColor(players, owner.color)
                        : (card.picked_by ?? "")
                    }`
                  : canPick
                    ? `Wybierz dla: ${pickerName ?? ""}`
                    : "Nie można teraz wybrać"
              }
              onClick={() =>
                // Klik dozwolonej karty → wybór dla aktualnego pickera (R8.5).
                // Gdy ``!canPick`` — wczesny return, BEZ requestu (R8.6).
                canPick &&
                pickerId !== null &&
                void run(() => pickStrategyCard(pickerId, card.initiative))
              }
            >
              {showImage ? (
                <img
                  className={styles.cardImage}
                  src={imageURL}
                  alt={name}
                  loading="lazy"
                  onError={() =>
                    setFailedImages((prev) => ({
                      ...prev,
                      [card.initiative]: true,
                    }))
                  }
                />
              ) : (
                // Fallback tekstowy (R8.8): dysk z inicjatywą + nazwa karty.
                <div className={styles.cardFallback}>
                  <span className={styles.disc}>{card.initiative}</span>
                  <span className={styles.name}>{name}</span>
                </div>
              )}

              {/* Pasek stanu: TG na karcie + właściciel, odróżnialnie od niewybranych. */}
              <div className={styles.cardMeta}>
                {card.trade_goods > 0 && (
                  <span className={styles.tg} title="Trade goods na karcie">
                    +{card.trade_goods} TG
                  </span>
                )}
                {isPicked && (
                  <span
                    className={styles.owner}
                    title={`Wybrana: ${
                      owner
                        ? playerNameForColor(players, owner.color)
                        : (card.picked_by ?? "")
                    }`}
                  >
                    <FactionMark player={owner} size={18} />
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
