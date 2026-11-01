import { useState, type ReactElement } from "react";
import cx from "clsx";
import { useParams } from "react-router-dom";
import { useGameState } from "@/api/useGameState";
import { useBoardEditor, useStrategyCards } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { SC_NAMES } from "@/entities/data/strategyCardColors";
import {
  getStrategyCardById,
  getStrategyCardByInitiative,
} from "@/entities/lookup/strategyCards";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon/CircularFactionIcon";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import {
  DetailsCard,
  type DetailsCardColor,
} from "@/shared/ui/DetailsCard";
import { Stack } from "@/ds";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
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

/*
 * Initiative → kolor sygnałowy ``DetailsCard`` (tooltipa z treścią karty).
 * Zgodnie z prośbą 12.2: 1=red … 8=violet — wartości dopuszczane przez typ
 * ``DetailsCardColor`` (patrz DetailsCard.tsx). Oddzielne od ``SC_TONE`` (to
 * surowe wartości CSS dla obwódki dysku, a tu nazwy wariantów DetailsCard).
 */
const SC_DETAILS_COLOR: Record<number, DetailsCardColor> = {
  1: "red",
  2: "orange",
  3: "yellow",
  4: "green",
  5: "teal",
  6: "cyan",
  7: "blue",
  8: "violet",
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
 * ``getStrategyCardById(card.id).imageURL`` — wariant wybrany przez backend),
 * oznaczenie wybranych kart i ich
 * właściciela, wyróżnienie aktualnego pickera oraz nagłówek z mówcą i komunikatami
 * stanu (R1.4/R1.5). Fallback tekstowy przy braku/błędzie grafiki (R8.8).
 *
 * PREZENTACJA (iteracja 12.2): DUŻE karty ułożone w ŁUK „wachlarz" (środkowe wyżej
 * i pionowo, brzegowe niżej i przechylone na zewnątrz) — geometria liczona z indeksu
 * karty względem środka rzędu i wstrzykiwana jako zmienne CSS ``--rot``/``--lift``.
 * Na HOVER/FOCUS karta prostuje się, powiększa, wychodzi na wierzch i pokazuje
 * TOOLTIP z treścią (``SmoothPopover`` + ``DetailsCard`` — ten sam wzorzec, co w
 * panelu gracza). To wyłącznie warstwa prezentacji; logika wyboru bez zmian.
 *
 * INTERAKCJA (zadanie 9.3): każda karta to klikalny ``<button>``. Klik WOLNEJ karty,
 * gdy jest wskazany picker → ``pickStrategyCard(pickerId, card.initiative)`` (R8.5).
 * Karta wybrana albo brak pickera / nie twoja kolej → blokada przez STRAŻNIK w
 * ``onClick`` (``canPick``), NIE przez atrybut ``disabled``: klik nie wysyła requestu
 * (R8.6). Świadomie bez ``disabled`` — wyłączony ``<button>`` nie emituje zdarzeń
 * hover/focus, więc tooltip musi działać na niewybieralnej karcie (iteracja 12.2).
 *
 * Źródła danych: WYŁĄCZNIE istniejące hooki (zero nowych):
 * - ``useGameState`` → ``gameState`` (faza, mówca, aktywny gracz) — ten sam
 *   selektor web-data, którego używa ``GameStatePanel`` (spójny stan, R8.2);
 * - ``useStrategyCards`` → pula kart zestawu + ich stan (``StrategyCardState[]``);
 * - ``useGameData`` → ``playerData`` (właściciel → ``FactionMark``/kolor);
 *   wybór wariantu karty robi backend (kanoniczny ``id``), nie ``strategyCardIdMap``;
 * - ``useBoardEditor`` → akcja ``pickStrategyCard`` (wybór karty dla pickera).
 */
export function StrategyCardTable(): ReactElement | null {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const { data: cards } = useStrategyCards();
  const gameData = useGameData();
  // Akcje: wybór karty (jak w ``GameStatePanel``) oraz przejście do następnej fazy
  // (``/phase/next``) — przycisk aktywny po skompletowaniu wyboru przez wszystkich.
  const { pickStrategyCard, nextPhase } = useBoardEditor();

  // Karty, których grafika nie wczytała się (``onError``) — przełączamy je na
  // fallback tekstowy (R8.8). Klucz = initiative.
  const [failedImages, setFailedImages] = useState<Record<number, boolean>>({});

  // Blokada podwójnego requestu w trakcie trwającego wyboru — ten sam wzorzec
  // ``busy``/``run``, co w ``StrategyCardPicker`` (GameStatePanel). Zapobiega
  // wysłaniu kolejnego ``pickStrategyCard`` zanim poprzedni się rozstrzygnie.
  const [busy, setBusy] = useState(false);

  // Karta z otwartym tooltipem (hover/focus). Klucz = initiative; ``null`` = brak.
  // Jeden stan dla całego rzędu (naraz tooltip pokazuje jedna karta).
  const [hovered, setHovered] = useState<number | null>(null);

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

  // Mówca: ``gameState.speaker`` to KOLOR — mapujemy na gracza i jego PEŁNĄ nazwę
  // frakcji (R1.4). ``speakerPlayer`` daje też ikonę frakcji w nagłówku.
  const speakerPlayer = gameState.speaker
    ? players.find((p) => p.color === gameState.speaker)
    : undefined;
  const speakerName = speakerPlayer
    ? getPlayerFactionDisplayName(speakerPlayer)
    : null;

  // Picker w podnagłówku (R1.5) — PEŁNA nazwa frakcji gracza + ikona (``pickerPlayer``
  // policzony wyżej). Gdy picker nieznany, pokazujemy komunikat zależny od tego, czy
  // wybór jest już kompletny (patrz ``allPicked``).
  const pickerName = pickerPlayer
    ? getPlayerFactionDisplayName(pickerPlayer)
    : null;

  // WYBÓR KOMPLETNY — ten sam warunek, co w ``StrategyCardPicker`` (GameStatePanel):
  // każdy gracz ma już ``pickCount`` kart (druga runda przy 3–4 graczach). Gdy
  // ``strategyPickCount`` nieznane (liczba graczy spoza 3..8) → bezpieczny ``false``,
  // nie twierdzimy błędnie „wszyscy wybrali". RULES.md 13. Dopiero wtedy NIE pokazujemy
  // „brak gracza do wskazania", lecz komunikat o końcu wyboru + przycisk następnej fazy.
  const pickCount = gameState.strategyPickCount ?? null;
  const allPicked =
    pickCount !== null &&
    players.length > 0 &&
    players.every((p) => (p.scs?.length ?? 0) >= pickCount);

  return (
    // Nakładka-wrapper: pełnoekranowy kontener, który WYŚRODKOWUJE panel kart w
    // poziomie i w pionie względem viewportu (``position: fixed`` + ``place-items:
    // center``). Sama nakładka nie przechwytuje zdarzeń (``pointer-events: none``);
    // to wewnętrzny ``.table`` ma ``pointer-events: auto``, więc karty pozostają
    // klikalne. Wyłącznie struktura/layout — ZERO zmian logiki interakcji i danych.
    <div className={styles.overlay}>
      <div className={styles.table} aria-label="Karty strategii na stole">
      {/*
       * Nagłówek w stylu AsyncTI4: WYŚRODKOWany tytuł fazy, a pod nim wiersz
       * (zawijalny) z aktualnym pickerem i mówcą — każdy z IKONĄ frakcji
       * (``FactionMark``) i PEŁNĄ nazwą frakcji (Requirement 1). Komunikaty braku
       * zostają bez ikony: brak pickera → „brak gracza do wskazania" (R1.5), brak
       * mówcy → „brak ustawionego mówcy" (R1.4).
       */}
      <div className={styles.header}>
        <h2 className={styles.heading}>Faza strategii</h2>
        <div className={styles.meta}>
          {/*
           * Stan wyboru:
           * - jest picker → „Teraz wybiera" + ikona/nazwa frakcji;
           * - wszyscy wybrali (``allPicked``) → komunikat końca wyboru + przycisk
           *   „Następna faza" (zamiast bezsensownego „brak gracza do wskazania");
           * - stan pośredni bez pickera (rzadki) → neutralny komunikat.
           */}
          {pickerName ? (
            <span className={styles.metaItem}>
              <span className={styles.metaLabel}>Teraz wybiera:</span>
              <FactionMark player={pickerPlayer} size={22} />
              <b className={styles.metaName}>{pickerName}</b>
            </span>
          ) : allPicked ? (
            <span className={styles.metaItem}>
              <b className={styles.metaName}>Wszyscy wybrali karty</b>
              <button
                type="button"
                className={styles.nextPhaseBtn}
                disabled={busy}
                onClick={() => void run(nextPhase)}
              >
                Następna faza
              </button>
            </span>
          ) : (
            <span className={styles.metaItem}>
              <span className={styles.metaName}>Wybór kart strategii</span>
            </span>
          )}
          {/* Mówca — ikona + pełna nazwa frakcji mówcy (lub komunikat braku). */}
          <span className={styles.metaItem}>
            <span className={styles.metaLabel}>Mówca:</span>
            {speakerName ? (
              <>
                <FactionMark player={speakerPlayer} size={22} />
                <b className={styles.metaName}>{speakerName}</b>
              </>
            ) : (
              <span className={styles.metaName}>brak ustawionego mówcy</span>
            )}
          </span>
        </div>
      </div>

      <div className={styles.cards} role="list">
        {cards.map((card, i, arr) => {
          // Definicja karty po KANONICZNYM ``id`` z backendu (wybór wariantu robi
          // rdzeń silnika — patrz strategyCards.ts). ``def`` daje grafikę (z
          // fallbackiem obrazu), teksty i nazwę (R8.1, R8.3). Gdy ``id`` spoza
          // lokalnych danych → cienki fallback po initiative. Fallback tekstowy,
          // gdy brak URL lub obrazek się nie wczytał (R8.8).
          const def =
            getStrategyCardById(card.id) ??
            getStrategyCardByInitiative(card.initiative);
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

          // GEOMETRIA ŁUKU (wachlarz wypukły do góry). Liczona z indeksu karty
          // względem środka rzędu — środek pionowo, brzegi przechylone na zewnątrz
          // i opuszczone w dół. ``offset`` od -mid do +mid (np. -3.5..+3.5 dla 8).
          const n = arr.length;
          const mid = (n - 1) / 2;
          const offset = i - mid;
          // Kąt obrotu: lewe karty w lewo (ujemny), prawe w prawo (dodatni).
          // Mniejszy kąt (było 4): przy obrocie wokół dolnego środka DUŻY kąt
          // podnosi górną krawędź skrajnych kart i to one „uciekały" wyżej —
          // łagodniejszy obrót trzyma je nisko (łuk wypukły do góry: środek wyżej,
          // rogi niżej).
          const rot = offset * 2.5;
          // Przesunięcie W DÓŁ rośnie kwadratowo od środka → łuk wypukły do góry
          // (środek lift≈0, brzegi NAJNIŻEJ). ``transform-origin: bottom center``.
          // Większy mnożnik (było 3): brzegi realnie opadają poniżej środka, więc
          // karty 1 i 8 są NIŻEJ niż pozostałe — kompensuje unoszenie przez obrót.
          const lift = Math.abs(offset) * Math.abs(offset) * 8;
          // SKALA per karta: skrajne karty (duży |offset|) delikatnie POWIĘKSZONE,
          // by zrównoważyć wrażenie, że przez obrót łuku są mniejsze (prośba:
          // „1 i 8 trochę większe"). Środek 1.0, brzegi do ~1.08.
          const scale = 1 + Math.abs(offset) * 0.024;

          // Tooltip otwarty dla tej karty? (klucz = initiative).
          const tooltipOpen = hovered === card.initiative;
          const detailsColor =
            SC_DETAILS_COLOR[card.initiative] ?? ("none" as DetailsCardColor);
          const primaryText = (def?.primaryTexts ?? []).join("\n\n");
          const secondaryText = (def?.secondaryTexts ?? []).join("\n\n");

          return (
            <SmoothPopover
              key={card.initiative}
              opened={tooltipOpen}
              position="top"
              onChange={(next) => {
                // Synchronizacja z wewnętrznym stanem popovera: gdy się zamyka,
                // a to właśnie ta karta — wyczyść ``hovered``.
                if (!next && hovered === card.initiative) setHovered(null);
              }}
            >
              <SmoothPopover.Target>
                <button
                  type="button"
                  role="listitem"
                  // ``pickable`` to WYŁĄCZNIE wizualna obwódka „do wyboru" na
                  // wolnych kartach, gdy jest wskazany picker — reużywa
                  // istniejącego ``canPick`` (bez nowej logiki).
                  className={cx(styles.card, canPick && styles.pickable)}
                  data-picked={isPicked || undefined}
                  // ``aria-disabled`` komunikuje stan niewybieralnej karty, ale
                  // element NIE dostaje natywnego ``disabled`` — dzięki temu
                  // wyłączony ``<button>`` dalej wyzwala hover/focus (a więc i
                  // tooltip) na KAŻDEJ karcie. Blokada kliku realizowana jest w
                  // strażniku ``onClick`` (poniżej), nie przez ``disabled``.
                  aria-disabled={!canPick || undefined}
                  // ``data-disabled`` steruje wyłącznie WYGASZENIEM w CSS
                  // (``.card[data-disabled]``) — zastępuje dawne ``.card:disabled``,
                  // które przestało działać po usunięciu atrybutu ``disabled``.
                  data-disabled={!canPick || undefined}
                  // Zmienne łuku + sygnał koloru dysku wstrzyknięte na kartę;
                  // CSS liczy z nich spoczynkowy ``transform`` (obrót + opad).
                  style={{
                    ["--scc" as string]: SC_TONE[card.initiative],
                    ["--rot" as string]: `${rot}deg`,
                    ["--lift" as string]: `${lift}px`,
                    ["--scale" as string]: `${scale}`,
                  }}
                  // Tooltip otwieramy na hover ORAZ focus (a11y), zamykamy na
                  // opuszczeniu/blur. To DODATEK — nie koliduje z klikiem/wyborem.
                  onMouseEnter={() => setHovered(card.initiative)}
                  onMouseLeave={() =>
                    setHovered((h) => (h === card.initiative ? null : h))
                  }
                  onFocus={() => setHovered(card.initiative)}
                  onBlur={() =>
                    setHovered((h) => (h === card.initiative ? null : h))
                  }
                  onClick={() => {
                    // STRAŻNIK kliku — po usunięciu ``disabled`` to jedyna
                    // blokada: klik karty zablokowanej (trwa request / brak
                    // pickera / nie twoja kolej) → wczesny return, BEZ requestu
                    // (R8.6). Klik dozwolonej karty → wybór dla pickera (R8.5).
                    if (busy || !canPick || pickerId === null) return;
                    void run(() => pickStrategyCard(pickerId, card.initiative));
                  }}
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

                  {/* Trade goods zaparkowane na karcie — pigułka w górnym rogu. */}
                  {card.trade_goods > 0 && (
                    <span className={styles.tg} title="Trade goods na karcie">
                      +{card.trade_goods} TG
                    </span>
                  )}

                  {/*
                   * WŁAŚCICIEL karty — czytelny baner u dołu: IKONA frakcji + PEŁNA
                   * NAZWA (zamiast małej ikonki w rogu). Nakładka na dolnej krawędzi
                   * obrazu, pełna szerokość karty; ``pointer-events: none`` — nie
                   * przechwytuje klików/hoveru (wybór i tooltip działają jak dotąd).
                   */}
                  {isPicked && (
                    <div className={styles.ownerBar}>
                      <FactionMark player={owner} size={22} />
                      <span className={styles.ownerName}>
                        {owner
                          ? getPlayerFactionDisplayName(owner)
                          : (card.picked_by ?? "")}
                      </span>
                    </div>
                  )}
                </button>
              </SmoothPopover.Target>

              {/*
               * TOOLTIP treści karty — ten sam wzorzec, co w panelu gracza
               * (Plot/Ability): ``DetailsCard`` w dropdownie popovera. Treść z
               * ``def`` (lookup po initiative); gdy ``def`` brak — fallback na
               * samą nazwę + initiative (bez wysypki).
               */}
              <SmoothPopover.Dropdown p={0}>
                <DetailsCard width={340} color={detailsColor}>
                  <Stack gap="md">
                    <DetailsCard.Title
                      title={`${def?.initiative ?? card.initiative} ${def?.name ?? name}`}
                      subtitle={`Strategy card · Initiative ${def?.initiative ?? card.initiative}`}
                    />
                    {primaryText && (
                      <DetailsCard.Section
                        title="Primary"
                        content={primaryText}
                      />
                    )}
                    {secondaryText && (
                      <DetailsCard.Section
                        title="Secondary"
                        content={secondaryText}
                      />
                    )}
                  </Stack>
                </DetailsCard>
              </SmoothPopover.Dropdown>
            </SmoothPopover>
          );
        })}
      </div>
      </div>
    </div>
  );
}
