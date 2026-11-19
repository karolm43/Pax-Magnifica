import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactElement,
} from "react";
import cx from "clsx";
import { IconCrown } from "@tabler/icons-react";
import { useParams } from "react-router-dom";
import { useGameState } from "@/api/useGameState";
import { useSettingsStore } from "@/state/appStore";
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
import { clampDragDelta } from "@/utils/keepOnScreen";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
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
 * KOLOR KARTY dla poświaty (hover-glow) — initiative → HEX koloru karty. Glow karty
 * bierze kolor STĄD, więc poświata jest w barwie danej karty (np. Technology niebieska,
 * Construction zielona), a nie w jednym wspólnym akcencie.
 *
 * ŹRÓDŁO: domyślnie używamy ``def.colourHexCode`` z danych karty (patrz render niżej).
 * Ta mapa to RĘCZNY OVERRIDE/fallback — gdy dana karta nie ma ``colourHexCode`` albo
 * chcesz wymusić inny odcień, wpisz HEX dla danej initiative poniżej. Wartości
 * startowe = oficjalne barwy kart strategii (możesz je dowolnie zmienić).
 */
const SC_HUE: Record<number, string> = {
  1: "#ec1c24", // Leadership — czerwony
  2: "#f69421", // Diplomacy — pomarańczowy
  3: "#fff200", // Politics — żółty
  4: "#39b54a", // Construction — zielony
  5: "#00a99d", // Trade — morski
  6: "#008ed4", // Warfare — błękit
  7: "#15489f", // Technology — niebieski
  8: "#752b90", // Imperial — fioletowy
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

/** Kolor gracza jako składowe ``"r g b"`` (do ``rgb(var(--owner-rgb) / a)``). */
function ownerRgb(player: PlayerData | undefined): string {
  const rgb = player?.color ? resolvePrimaryRgb(player.color) : undefined;
  return rgb ? `${rgb.red} ${rgb.green} ${rgb.blue}` : "148 163 184";
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
  const { pickStrategyCard, nextPhase, skipPhase } = useBoardEditor();
  const skipPhasesEnabled = useSettingsStore((s) => s.settings.skipPhases);

  // Karty, których grafika nie wczytała się (``onError``) — przełączamy je na
  // fallback tekstowy (R8.8). Klucz = initiative.
  const [failedImages, setFailedImages] = useState<Record<number, boolean>>({});

  // Blokada podwójnego requestu w trakcie trwającego wyboru — ten sam wzorzec
  // ``busy``/``run``, co w ``StrategyCardPicker`` (GameStatePanel). Zapobiega
  // wysłaniu kolejnego ``pickStrategyCard`` zanim poprzedni się rozstrzygnie.
  const [busy, setBusy] = useState(false);
  // Checks and Balances (RULES.md 51.6): komu oddać wybraną kartę.
  const [recipient, setRecipient] = useState<string | null>(null);

  // Karta z otwartym tooltipem (hover/focus). Klucz = initiative; ``null`` = brak.
  // Jeden stan dla całego rzędu (naraz tooltip pokazuje jedna karta).
  const [hovered, setHovered] = useState<number | null>(null);

  // MINIMALIZACJA panelu (prośba użytkownika): gdy ``true``, panel zwija się do
  // kompaktowego paska nagłówka (same karty schowane), żeby nie zasłaniać mapy.
  // Stan czysto lokalny/wizualny — nie dotyka logiki wyboru ani danych gry.
  const [minimized, setMinimized] = useState(false);

  // ANIMACJA WEJŚCIA — JEDNORAZOWA, sterowana stanem (nie samym CSS). Problem z
  // czystym CSS: panel re-renderuje się często (hover/busy/stan gry), a animacje z
  // ``fill-mode`` przy skumulowanych opóźnieniach powodowały miganie/znikanie kart.
  // Rozwiązanie: ``intro`` jest ``true`` tylko na starcie; po odegraniu pełnej
  // sekwencji (baner → kaskada kart) zdejmujemy klasy animacji (``data-intro``
  // schodzi), więc kolejne re-rendery NIE dotykają już animacji — zero migania.
  const [intro, setIntro] = useState(true);
  // Karty MONTUJĄ SIĘ dopiero PO wejściu banera (prośba użytkownika: „zacznij dopiero
  // po bannerze"). Sterowanie przez MOUNT (nie tylko opóźnienie CSS) daje twardą
  // gwarancję kolejności: dopóki ``showCards`` jest ``false``, rząd kart nie istnieje
  // w DOM, więc nie może „już być" na starcie. Po banerze flaga wchodzi i karty
  // rozdają się kaskadowo (każda animuje wejście przy swoim montażu).
  const [showCards, setShowCards] = useState(false);
  useEffect(() => {
    // 1) Po wejściu banera (~0.45s) montujemy karty → zaczyna się kaskada.
    const tCards = window.setTimeout(() => setShowCards(true), 480);
    // 2) Po pełnej kaskadzie zdejmujemy ``intro`` → reguły animacji znikają, więc
    //    późniejsze re-rendery (hover/wybór) nie migają kartami.
    const tDone = window.setTimeout(() => setIntro(false), 1700);
    return () => {
      window.clearTimeout(tCards);
      window.clearTimeout(tDone);
    };
  }, []);

  // PRZESUWANIE OKNA (prośba użytkownika): przesunięcie panelu względem jego
  // wyśrodkowanej pozycji (``dx``/``dy`` w px). Panel domyślnie stoi na środku
  // (overlay = ``place-items: center``); drag dokłada ``translate(dx, dy)``.
  const [offset, setOffset] = useState<{ dx: number; dy: number }>({
    dx: 0,
    dy: 0,
  });
  // Ref do stanu przeciągania — trzyma punkt startowy kursora i offsetu, żeby
  // handlery ``pointermove`` nie zależały od re-renderów (unikamy stale closure).
  const dragRef = useRef<{
    startX: number;
    startY: number;
    baseDx: number;
    baseDy: number;
  } | null>(null);

  // Start przeciągania — tylko z „uchwytu" (nagłówka). Pomijamy drag, gdy klik
  // padł na element interaktywny (przycisk collapse/next phase), żeby nie kradł
  // kliknięcia. Rejestrujemy globalne listenery na czas przeciągania.
  const onHandlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if ((e.target as HTMLElement).closest("button")) return;
      e.preventDefault();
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        baseDx: offset.dx,
        baseDy: offset.dy,
      };
      // Stół zostaje CAŁY na ekranie (nie da się go wyciągnąć poza widok).
      const box = e.currentTarget.parentElement?.getBoundingClientRect();

      const onMove = (ev: PointerEvent) => {
        const d = dragRef.current;
        if (!d) return;
        const raw = { dx: ev.clientX - d.startX, dy: ev.clientY - d.startY };
        const step = box ? clampDragDelta(box, raw.dx, raw.dy) : raw;
        setOffset({ dx: d.baseDx + step.dx, dy: d.baseDy + step.dy });
      };
      const onUp = () => {
        dragRef.current = null;
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
      };
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
    },
    [offset.dx, offset.dy],
  );

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

  // Mówca: ``gameState.speaker`` to KOLOR — mapujemy na gracza (korona na jego chipie
  // w kolejce wyboru, R1.4).
  const speakerPlayer = gameState.speaker
    ? players.find((p) => p.color === gameState.speaker)
    : undefined;

  // WYBÓR KOMPLETNY — ten sam warunek, co w ``StrategyCardPicker`` (GameStatePanel):
  // każdy gracz ma już ``pickCount`` kart (druga runda przy 3–4 graczach). Gdy
  // ``strategyPickCount`` nieznane (liczba graczy spoza 3..8) → bezpieczny ``false``,
  // nie twierdzimy błędnie „wszyscy wybrali". RULES.md 13. Dopiero wtedy NIE pokazujemy
  // „brak gracza do wskazania", lecz komunikat o końcu wyboru + przycisk następnej fazy.
  const pickCount = gameState.strategyPickCount ?? null;
  // Kolejka wyboru = porządek mówcy (``seatingOrder`` rotuje od mówcy): kto wybiera teraz i
  // kto co już wziął - widoczne od razu, bez szukania po kartach.
  const pickOrder = (gameState.seatingOrder ?? [])
    .map((color) => players.find((p) => p.color === color))
    .filter((p): p is PlayerData => p !== undefined);
  const orderPlayers = pickOrder.length > 0 ? pickOrder : players;
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
      <div
        className={styles.table}
        data-minimized={minimized || undefined}
        // ``data-intro`` włącza animacje wejścia TYLKO na starcie (patrz stan
        // ``intro``); po odegraniu sekwencji schodzi, więc re-rendery nie migają.
        data-intro={intro || undefined}
        aria-label="Strategy Cards on the table"
        style={{
          transform: `translate(${offset.dx}px, ${offset.dy}px)`,
        }}
      >
      {/*
       * Nagłówek: WYŚRODKOWany tytuł fazy i pod nim kolejka wyboru — chipy z IKONĄ
       * i PEŁNĄ nazwą frakcji, wybrane karty, „picking…” u wybierającego, korona mówcy.
       */}
      <div
        className={styles.header}
        onPointerDown={onHandlePointerDown}
        title="Drag to move"
      >
        {/*
         * Przycisk ZWIŃ/ROZWIŃ (prośba użytkownika) — NA BANERZE nagłówka, w jego
         * prawym rogu. Wyraźny chip ze ściętym narożnikiem, spójny z banerem. Tylko
         * prezentacja: nie zmienia stanu wyboru ani danych gry.
         */}
        <button
          type="button"
          className={styles.minimizeBtn}
          aria-expanded={!minimized}
          aria-label={minimized ? "Expand strategy cards" : "Collapse strategy cards"}
          title={minimized ? "Expand strategy cards" : "Collapse strategy cards"}
          // Przycisk siedzi na „uchwycie" do przeciągania (nagłówku); ``onPointerDown``
          // zatrzymujemy, żeby klik w collapse nie startował przeciągania okna.
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => setMinimized((m) => !m)}
        >
          {minimized ? "▢" : "–"}
        </button>
        <h2 className={styles.heading}>Strategy Phase</h2>
        {/*
         * Kto teraz wybiera i kto jest mówcą pokazują CHIPY kolejki poniżej (chip
         * wybierającego świeci + „picking…”, mówca ma koronę) — bez osobnego wiersza
         * „Now picking / Speaker”, który to dublował (decyzja użytkownika: mniej tłoku).
         * Wiersz meta zostaje tylko na koniec wyboru („Next phase”) i przeskok God-Mode.
         */}
        {(allPicked || skipPhasesEnabled) && (
          <div className={styles.meta}>
            {allPicked && (
              <span className={styles.metaItem}>
                <b className={styles.metaName}>Everyone has picked a card</b>
                <button
                  type="button"
                  className={styles.nextPhaseBtn}
                  disabled={busy}
                  onClick={() => void run(nextPhase)}
                >
                  Next phase
                </button>
              </span>
            )}
            {/* God-Mode (testy): przeskok fazy — auto-wybiera brakujące karty. */}
            {skipPhasesEnabled && !allPicked && (
              <button
                type="button"
                className={styles.nextPhaseBtn}
                disabled={busy}
                onClick={() => void run(skipPhase)}
                title="God-Mode: auto-pick the remaining cards and skip to the action phase"
              >
                Skip phase
              </button>
            )}
          </div>
        )}
        <ol className={styles.pickOrder} aria-label="Pick order">
          {orderPlayers.map((p) => {
            const mine = cards.filter((c) => c.picked_by === p.discordId);
            const now = pickerColor !== null && p.color === pickerColor;
            const names = mine.map((c) => c.name || SC_NAMES[c.initiative]).join(", ");
            return (
              <li
                key={p.discordId}
                className={styles.pickSeat}
                data-now={now || undefined}
                data-done={mine.length > 0 || undefined}
                style={{ ["--owner-rgb" as string]: ownerRgb(p) }}
                title={`${getPlayerFactionDisplayName(p)}${speakerPlayer?.discordId === p.discordId ? " (Speaker)" : ""}${names ? ` - ${names}` : now ? " - picking now" : ""}`}
              >
                <FactionMark player={p} size={24} />
                <span className={styles.pickSeatName}>{getPlayerFactionDisplayName(p)}</span>
                {speakerPlayer?.discordId === p.discordId && (
                  <IconCrown
                    size={14}
                    className={styles.pickSeatSpeaker}
                    role="img"
                    aria-label="Speaker"
                  />
                )}
                {mine.map((c) => (
                  <b
                    key={c.initiative}
                    className={styles.pickSeatCard}
                    style={{ ["--scc" as string]: SC_TONE[c.initiative] }}
                  >
                    {c.initiative} {c.name || SC_NAMES[c.initiative]}
                  </b>
                ))}
                {mine.length === 0 && now && <small className={styles.pickSeatNow}>picking…</small>}
              </li>
            );
          })}
        </ol>
      </div>

      {/*
       * Rząd kart: ukrywany po zwinięciu panelu (``minimized``) oraz NIEMONTOWANY,
       * dopóki baner nie wejdzie (``showCards`` — twarda gwarancja, że karty
       * startują PO banerze). Gdy nie montujemy, rezerwujemy wysokość placeholderem,
       * żeby panel nie „podskakiwał" w momencie wejścia kart.
       */}
      {!minimized && !showCards && (
        <div className={styles.cardsPlaceholder} aria-hidden="true" />
      )}
      {!minimized && gameState.strategyGivesCards && pickerId !== null ? (
        <div className={styles.recipients} role="group" aria-label="Give the chosen card to">
          <span>Checks and Balances - give the chosen card to:</span>
          {players
            .filter(
              (p) =>
                p.discordId !== pickerId &&
                (pickCount === null || (p.scs?.length ?? 0) < pickCount),
            )
            .map((p) => (
              <button
                key={p.discordId}
                type="button"
                className={styles.recipientBtn}
                aria-pressed={recipient === p.discordId}
                onClick={() => setRecipient(p.discordId)}
              >
                <FactionMark player={p} size={18} />
                {getPlayerFactionDisplayName(p)}
              </button>
            ))}
        </div>
      ) : null}
      {!minimized && showCards && (
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
                    // KOLOR KARTY dla poświaty: preferuj ``colourHexCode`` z danych
                    // karty (prawdziwa barwa danego wariantu), a gdy brak — ręczny
                    // override z mapy ``SC_HUE`` po initiative.
                    ["--sc-hue" as string]:
                      def?.colourHexCode ?? SC_HUE[card.initiative],
                    ["--rot" as string]: `${rot}deg`,
                    ["--lift" as string]: `${lift}px`,
                    ["--scale" as string]: `${scale}`,
                    // Indeks karty dla KASKADOWEGO wejścia (animacja ``cardIn`` liczy
                    // opóźnienie od środka wachlarza ku brzegom — patrz CSS).
                    ["--i" as string]: `${i}`,
                    ["--owner-rgb" as string]: ownerRgb(owner),
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
                    void run(() =>
                      pickStrategyCard(pickerId, card.initiative, recipient ?? undefined),
                    );
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

                  {/*
                   * Trade goods zaparkowane na karcie — GRAFIKA żetonu TG (``/tg.png``,
                   * ten sam asset, co w ``StrategyCard``/``StoresStrip``) z liczbą,
                   * zamiast tekstu „+N TG". Pigułka w górnym rogu; ``pointer-events:
                   * none`` — nie przechwytuje klików/hoveru.
                   */}
                  {card.trade_goods > 0 && (
                    <span
                      className={styles.tg}
                      title={`${card.trade_goods} Trade Goods on the card`}
                    >
                      <img className={styles.tgIcon} src="/tg.png" alt="" />
                      <b className={styles.tgCount}>{card.trade_goods}</b>
                    </span>
                  )}

                  {/*
                   * WŁAŚCICIEL karty (decyzja użytkownika 2026-11-18): karta wybrana jest
                   * mocno wyszarzona; plakietka
                   * w kolorze gracza wystaje NAD kartę (nie zasłania nazwy karty).
                   */}
                  {isPicked && (
                    <>
                      <span className={styles.ownerTag}>
                        <FactionMark player={owner} size={20} />
                        <span className={styles.ownerTagName}>
                          {owner ? getPlayerFactionDisplayName(owner) : (card.picked_by ?? "")}
                        </span>
                      </span>
                    </>
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
      )}
      </div>
    </div>
  );
}
