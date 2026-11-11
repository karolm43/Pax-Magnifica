// Kontener kreatora setupu (Setup_Wizard).
//
// Odpowiedzialności (zadanie 11.3):
//  1. Renderuje BIEŻĄCY krok wg uporządkowanej sekwencji `SETUP_STEPS` (R14.1). Mapowanie
//     „id kroku → komponent" trzyma lekki rejestr `STEP_COMPONENTS` (Step_Players —
//     gracze/mapa/sterowanie, Step_Faction — wybór frakcji, Step_SeatColor — miejsce
//     i kolor z podpowiedzią kolorów frakcji). Wszystkie kroki są
//     pełnoekranowymi scenami (bez ramki kreatora) i same rysują pasek górny z akcjami
//     nawigacji (`StageActions`). Wybór technologii startowych jest wbudowany w panel
//     podglądu frakcji (`FactionSummary`).
//  2. Blokuje „Dalej"/„Start" przy niespełnionej walidacji (R7.4–R7.6, R9.2/R9.5, R10.2)
//     — logika w czystej funkcji `validateSetup` ze store'a.
//  3. Mapuje stan store'a na `NewGameRequest` (`toNewGameRequest`) i wysyła `/game/new`.
//
// Kontener jest celowo „cienki": cała walidacja i mapowanie żyją w `useSetupStore.ts`
// (testowalne bez Reacta), tu zostaje tylko spięcie stanu z UI i obsługa wysyłki.

import { seatLobbyPlayers, useLobbyRole, useSetupSync } from "@/domains/network/setupSync";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { useEffect, useMemo, useState, type ComponentType } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useSettingsStore } from "@/state/appStore";
import {
  useFactions,
  useEngineConfig,
  createNewGame,
  type FactionInfo,
} from "@/api/useNewGame";
import { SETUP_STEPS, type SetupStepId } from "./setupSteps";
import {
  currentStep,
  toNewGameRequest,
  useSetupStore,
  validateSetup,
  validateStep,
} from "./useSetupStore";
import Step_Players from "./steps/Step_Players";
import Step_Faction from "./steps/Step_Faction";
import Step_SeatColor from "./steps/Step_SeatColor";
import GameIntro from "./GameIntro";
import { loadIntroPlayers, type IntroPlayer } from "./introPlayers";

/**
 * Propsy współdzielone przez komponenty kroków. Każdy krok dostaje listę frakcji
 * (z `/factions`) i mapę po id — reszta danych (sloty, akcje) pochodzi bezpośrednio ze
 * store'a przez `useSetupStore`, więc kroki nie potrzebują prop-drillingu stanu.
 */
export interface SetupStepProps {
  factions: FactionInfo[];
  factionById: Map<string, FactionInfo>;
  /** Akcje nawigacji paska górnego sceny (każdy krok jest sceną pełnoekranową). */
  stage?: StageActions;
}

/**
 * Akcje paska górnego sceny pełnoekranowej (kroki nie mają ramki kreatora, więc
 * „Wstecz", „Dalej" i „Start gry" renderują same w swoim pasku).
 */
export interface StageActions {
  /** Krok wstecz; na pierwszym kroku wraca do menu głównego. */
  onBack: () => void;
  /** Przejście do następnego kroku (na ostatnim kroku — to samo co `onSubmit`). */
  onNext: () => void;
  onSubmit: () => void;
  submitting: boolean;
  /** Czy to ostatni krok (przycisk akcji = „Start game", nie „Next"). */
  isLastStep: boolean;
  /** Czy bieżący krok przeszedł walidację (przycisk akcji aktywny). */
  canSubmit: boolean;
  /** Komunikat walidacji / błąd wysyłki (albo `null`). */
  message: string | null;
}

/** Kroki rysowane na całym ekranie, poza ramką kreatora (sceny) — dziś wszystkie. */
export const STAGE_STEP_IDS: ReadonlySet<SetupStepId> = new Set([
  "players",
  "faction",
  "seat-color",
]);

/**
 * Rejestr „id kroku → komponent". Każdy krok kreatora ma tu swój komponent; dodanie
 * nowego kroku (np. przyszły draft slice) = nowy wpis bez zmian w samym kontenerze.
 */
const STEP_COMPONENTS: Record<SetupStepId, ComponentType<SetupStepProps>> = {
  players: Step_Players,
  faction: Step_Faction,
  "seat-color": Step_SeatColor,
};

/**
 * Kreator setupu nowej gry. Steruje nawigacją po krokach (`SETUP_STEPS`) i — na ostatnim
 * kroku — wysyła konfigurację do backendu, po czym przechodzi do widoku planszy.
 *
 * @param onExit wywoływane przez „Wstecz" na pierwszym kroku (powrót do menu głównego).
 */
export default function SetupWizard({ onExit }: { onExit?: () => void } = {}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: factions } = useFactions();
  const { data: engineConfig } = useEngineConfig();
  const seatPositions = engineConfig?.seats;

  const slots = useSetupStore((s) => s.slots);
  const mapString = useSetupStore((s) => s.mapString);
  const currentStepIndex = useSetupStore((s) => s.currentStepIndex);
  const nextStep = useSetupStore((s) => s.nextStep);
  const prevStep = useSetupStore((s) => s.prevStep);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Uczestnicy do planszy otwierającej; `null` = intro nie jest pokazywane.
  const [introPlayers, setIntroPlayers] = useState<IntroPlayer[] | null>(null);
  // Tryb administratora (szybkie testy) pomija planszę otwierającą i wchodzi prosto do gry.
  const adminFastMode = useSettingsStore((s) => s.settings.adminFastMode);
  // Lobby sieciowe (RULES.md 44.5a): ten sam kreator, wspólny na żywo. Host prowadzi kroki,
  // gość wybiera tylko swoją frakcję/kolor/miejsce.
  const { data: me } = useNetworkMe();
  const networkLobby = me?.network === true;
  // Gość: host wystartował grę → ta sama plansza otwierająca co u hosta, potem gra.
  const [guestStarted, setGuestStarted] = useState(false);
  useSetupSync(networkLobby, () => setGuestStarted(true));
  const isGuest = useLobbyRole((r) => r.active && r.isGuest);

  // Mapa frakcji po id — do walidacji (liczba wymaganych tech) i mapowania żądania.
  const factionById = useMemo(() => {
    const map = new Map<string, FactionInfo>();
    for (const f of factions ?? []) map.set(f.id, f);
    return map;
  }, [factions]);

  const step = currentStep(currentStepIndex);
  const isLastStep = currentStepIndex >= SETUP_STEPS.length - 1;

  // Walidacja bieżącego kroku — blokuje „Dalej". Sprawdza TYLKO reguły tego kroku,
  // więc np. brak wyboru technologii (krok późniejszy) nie blokuje wyjścia z kroku
  // graczy. To była przyczyna „nie da się przejść dalej" dla frakcji z wyborem tech.
  const stepError = useMemo(
    () => validateStep(step.id, slots, factionById, mapString),
    [step.id, slots, factionById, mapString],
  );

  // Pełna walidacja — wymagana dopiero przy „Start" (ostatni krok): komplet reguł.
  const fullError = useMemo(
    () => validateSetup(slots, factionById, mapString),
    [slots, factionById, mapString],
  );

  // Komunikat pod krokiem: na ostatnim kroku pokazuje pełny błąd (co jeszcze brakuje),
  // na wcześniejszych — błąd bieżącego kroku.
  const validationError = isLastStep ? fullError : stepError;

  const StepComponent = STEP_COMPONENTS[step.id];

  const handleSubmit = async () => {
    if (!factions || validationError) return;
    setError(null);
    setSubmitting(true);
    try {
      const request = toNewGameRequest(slots, mapString, factionById, seatPositions);
      await createNewGame(request);
      // Lobby: właściciele slotów (host, goście) siadają jako p{i+1}; goście same wchodzą do gry.
      if (networkLobby) await seatLobbyPlayers();
      // Nowa gra = nowy stan; wymuś świeży fetch web-data (staleTime: Infinity).
      await queryClient.invalidateQueries({ queryKey: ["playerData"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error while creating the game.");
      setSubmitting(false);
      return;
    }
    // Plansza otwierająca (tytuł, kronika, uczestnicy) przed pierwszą fazą strategii.
    // To tylko oprawa: gdy nie da się pobrać uczestników, wchodzimy prosto do gry.
    // Tryb administratora (szybkie testy) świadomie pomija intro — od razu do gry.
    if (!adminFastMode) {
      try {
        const players = await loadIntroPlayers(factionById);
        if (players.length > 0) {
          setIntroPlayers(players); // `submitting` zostaje, dopóki intro się nie skończy
          return;
        }
      } catch {
        /* intro pominięte */
      }
    }
    navigate("/game");
  };

  useEffect(() => {
    if (!guestStarted) return;
    if (adminFastMode) {
      navigate("/game");
      return;
    }
    let cancelled = false;
    loadIntroPlayers(factionById)
      .then((players) => {
        if (cancelled) return;
        if (players.length > 0) setIntroPlayers(players);
        else navigate("/game");
      })
      .catch(() => {
        if (!cancelled) navigate("/game"); // intro to tylko oprawa
      });
    return () => {
      cancelled = true;
    };
    // Jednorazowo po starcie gry (frakcje są już wczytane — gość właśnie je wybierał).
  }, [guestStarted]);

  // Plansza otwierająca nakłada się na kreator (portal) aż do wejścia w grę.
  const intro = introPlayers && (
    <GameIntro players={introPlayers} onFinish={() => navigate("/game")} />
  );

  return (
    <>
      <StepComponent
        factions={factions ?? []}
        factionById={factionById}
        stage={
          isGuest
            ? {
                // Gość: kroki prowadzi host; „Wstecz" = wyjście z lobby.
                onBack: onExit ?? (() => undefined),
                onNext: () => undefined,
                onSubmit: () => undefined,
                submitting: false,
                isLastStep,
                canSubmit: false,
                message: "The host moves everyone to the next step.",
              }
            : {
                // Pierwszy krok nie ma „poprzedniego" — wraca do menu głównego.
                onBack: currentStepIndex === 0 ? (onExit ?? (() => undefined)) : prevStep,
                onNext: nextStep,
                onSubmit: () => void handleSubmit(),
                submitting,
                isLastStep,
                canSubmit: validationError === null && !!factions,
                message: error ?? validationError,
              }
        }
      />
      {intro}
    </>
  );
}
