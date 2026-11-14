import { useEffect, useState, type ReactNode } from "react";
import { NetworkPanel } from "@/domains/network/NetworkPanel";
import { useDeckSearchStore } from "@/domains/search/deckSearchStore";
import { useParams } from "react-router-dom";
import { AppShell, Box, Tabs } from "@/ds";
import { SiteHeader } from "@/layout/SiteHeader";
import classes from "@/shared/ui/map/MapUI.module.css";
import ScoreBoard from "@/domains/objectives/components/ScoreBoard/ScoreBoard";
import { UpdateNeededScreen } from "@/domains/game-shell/components/chrome/UpdateNeededScreen";
import { SettingsModal } from "@/domains/settings/components/SettingsModal";
import { SystemDossierModal } from "@/domains/map/components/SystemDossier/SystemDossierModal";
import { MoveUnitsModal } from "@/domains/map/components/MoveUnitsModal";
import { MoveQuantityModal } from "@/domains/map/components/MoveQuantityModal";
import { MultiSelectHud } from "@/domains/map/components/MultiSelectHud";
import { LoadTransportModal } from "@/domains/map/components/LoadTransportModal";
import { CapacityModal } from "@/domains/map/components/CapacityModal";
import { FleetPoolModal } from "@/domains/map/components/FleetPoolModal";
import { BattleOverlay } from "@/domains/battle/BattleOverlay";
import { DiceStageHost } from "@/domains/dice/DiceStageHost";
import { TableRollWatcher } from "@/domains/dice/TableRollWatcher";
import { NotificationArea } from "@/domains/game-shell/components/Notifications";
import { AudioDirector } from "@/shared/audio/AudioDirector";
import { RelicRevealWatcher } from "@/domains/relics/RelicRevealWatcher";
import { InvasionOverlay } from "@/domains/invasion/InvasionOverlay";
import { ExplorationOverlay } from "@/domains/exploration/ExplorationOverlay";
import { DecisionCenter } from "@/domains/offers/AbilityPrompts";
import { ActiveEffectsPanel } from "@/domains/effects/ActiveEffectsPanel";
import { ThundersEdgeOverlay } from "@/domains/thunders-edge/ThundersEdgeOverlay";
import { ProductionOverlay } from "@/domains/production/ProductionOverlay";
import { AgendaOverlay } from "@/domains/agenda/AgendaOverlay";
import { GameSetupOverlay } from "@/domains/setup/GameSetupOverlay";
import { CombatModal } from "@/domains/map/components/CombatModal";
import { SecondaryDecisionModal } from "@/domains/game-shell/components/SecondaryDecisionModal";
import { KeyboardShortcutsModal } from "@/domains/game-shell/components/KeyboardShortcutsModal";
import { GameContextProvider } from "@/state/GameContextProvider";
import { useSettingsStore } from "@/state/appStore";
import {
  useGameData as useGameContext,
  useGameDataState,
} from "@/state/useGameContext";
import PlayersTab from "@/domains/game-shell/components/PlayersTab";
import { PlayerTab } from "@/domains/player/components/PlayerTab/PlayerTab";
import { TabsControls } from "@/domains/game-shell/components/TabsControls";
import { useTabManagement } from "@/domains/tabs/hooks/useTabManagement";
import GeneralArea from "@/domains/game-shell/components/GeneralArea";
import { PannableMapView } from "@/domains/game-shell/components/layouts/PannableMapView";
import { MapLoadingState } from "@/domains/map/components/MapLoadingState";
import { MapViewportLoader } from "@/shared/ui/primitives/MapViewportLoader";
import { isMobileDevice } from "@/utils/isTouchDevice";
import { NavigationDrawer } from "@/domains/game-shell/components/navigation/NavigationDrawer";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { usePageThemeClass } from "@/hooks/usePageThemeClass";
import { PlayerDataErrorAlert } from "@/shared/ui/PlayerDataErrorAlert";
import { MAIN_TAB_CONFIGS } from "@/domains/game-shell/components/mainTabs";
import { TabPanelSection } from "@/domains/game-shell/components/TabPanelSection";
import { APP_HEADER_HEIGHT } from "@/shared/ui/AppHeader";
import { TabActiveContext } from "@/hooks/useIsTabActive";
import { HeaderGameControls } from "@/shared/ui/HeaderGameControls";
import { DEFAULT_GAME_ID } from "@/config";
import { VictoryScreen } from "@/domains/victory/VictoryScreen";
import { MobileHandSheet } from "@/domains/game-shell/components/SecretHand";
import { MobileEventsSheet } from "@/domains/game-shell/components/GameEventPanel";
import { useSecretHandAccess } from "@/domains/game-shell/components/SecretHand/useSecretHandAccess";

const REQUIRED_VERSION_SCHEMA = 5;

type TabContentProps = {
  gameId: string;
  ready: boolean;
  isError: boolean;
  children: ReactNode;
};

/**
 * Every tab reads the same web-data document, so they all wait and fail the same
 * way. Without this they rendered an empty panel for both, which is why a slow
 * load and a dead game looked identical.
 */
function TabContent({ gameId, ready, isError, children }: TabContentProps) {
  if (ready) return <>{children}</>;
  if (isError) return <PlayerDataErrorAlert gameId={gameId} />;
  return <MapViewportLoader label="Acquiring game state" />;
}

function GameMapContent() {
  const data = useGameContext();
  const gameDataState = useGameDataState();
  const isError = !!gameDataState?.isError;
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;

  const { activeTabs, changeTab, removeTab } = useTabManagement();
  const settings = useSettingsStore((state) => state.settings);
  const handlers = useSettingsStore((state) => state.handlers);
  const versionSchema = data?.versionSchema;
  const hasChannelLinks = !!(data?.actionsJumpLink || data?.tableTalkJumpLink);

  const [drawerOpened, setDrawerOpened] = useState(false);
  const [activeTab, setActiveTab] = useState("map");
  /* Desktop reaches the hand and event log through the floating map toolbar,
     which phones and the other desktop tabs do not show, so there they get
     their own entry points and sheets. */
  const { canViewSecretHand } = useSecretHandAccess();
  const isMobile = isMobileDevice();
  const onMapTab = activeTab === "map";
  const [handOpened, setHandOpened] = useState(false);
  const [eventsOpened, setEventsOpened] = useState(false);
  const openHand = canViewSecretHand ? () => setHandOpened(true) : undefined;
  const openEvents = () => setEventsOpened(true);
  const mobileOpenHand = isMobile ? openHand : undefined;
  const mobileOpenEvents = isMobile ? openEvents : undefined;
  const desktopOpenHand = !isMobile && !onMapTab ? openHand : undefined;
  const desktopOpenEvents = !isMobile && !onMapTab ? openEvents : undefined;
  // Tabs mount on first visit and then stay mounted (hidden), so switching back
  // to the map doesn't rebuild ~10k components every time.
  const [visitedTabs, setVisitedTabs] = useState(() => new Set(["map"]));

  const changeActiveTab = (value: string) => {
    setActiveTab(value);
    setVisitedTabs((prev) =>
      prev.has(value) ? prev : new Set(prev).add(value),
    );
  };

  /* Plansza zajmuje cały ekran i NIE przewija strony: bez tej blokady okno/lista wystające
     poza ekran dokładało pasek przewijania z prawej i przeskok całego układu. */
  useEffect(() => {
    if (isMobile || !onMapTab) return;
    const root = document.documentElement;
    const previous = root.style.overflow;
    root.style.overflow = "hidden";
    return () => {
      root.style.overflow = previous;
    };
  }, [isMobile, onMapTab]);

  /* Wyszukiwarka planszy otworzyła talię: okna talii żyją w zakładce General. */
  const deckRequest = useDeckSearchStore((state) => state.request);
  useEffect(() => {
    if (deckRequest) changeActiveTab("general");
  }, [deckRequest]);

  const activePlayerName = data?.playerData?.find((p) => p.active)?.userName;
  useDocumentTitle(
    activePlayerName
      ? `⏳ ${activePlayerName} · ${gameId} · Custodian Engine`
      : `${gameId} · Custodian Engine`,
  );

  if (
    data &&
    !gameDataState?.isLoading &&
    (!versionSchema || versionSchema < REQUIRED_VERSION_SCHEMA)
  ) {
    return (
      <UpdateNeededScreen
        gameId={gameId}
        activeTabs={activeTabs}
        changeTab={changeTab}
        removeTab={removeTab}
      />
    );
  }

  return (
    <AppShell header={{ height: APP_HEADER_HEIGHT }}>
      <SiteHeader currentMapId={gameId}>
        <HeaderGameControls />
      </SiteHeader>

      <AppShell.Main>
        <Box
          className={classes.mainBackground}
          mod={{ "channel-links": hasChannelLinks }}
        >
          <Tabs
            value={activeTab}
            onChange={(value) => changeActiveTab(value || "map")}
            h={{ base: "100vh", sm: "calc(100vh - var(--app-header-height))" }}
            keepMounted
          >
            <Tabs.List className={classes.tabsList}>
              {MAIN_TAB_CONFIGS.map((tab) => {
                if (tab.hideOnMobile && isMobileDevice()) {
                  return null;
                }

                const Icon = tab.Icon;
                return (
                  <Tabs.Tab
                    key={tab.value}
                    value={tab.value}
                    className={classes.tabsTab}
                    leftSection={<Icon size={16} />}
                    visibleFrom={tab.visibleFrom}
                  >
                    {tab.label}
                  </Tabs.Tab>
                );
              })}
              <TabsControls
                onMenuClick={() => setDrawerOpened(true)}
                onCardsClick={mobileOpenHand}
                onEventsClick={mobileOpenEvents}
                onDesktopCardsClick={desktopOpenHand}
                onDesktopEventsClick={desktopOpenEvents}
                onTryDecalsClick={() =>
                  window.dispatchEvent(new CustomEvent("toggleTryDecals"))
                }
              />
            </Tabs.List>

            {/* Map Tab
                The board, both HUD decks and the floating controls only mount
                over real data — chrome calibrated to nothing is the artifact
                this replaces. */}
            <Tabs.Panel value="map" h="calc(100% - var(--map-tabs-height))">
              <TabActiveContext value={activeTab === "map"}>
                {!data ? (
                  <MapLoadingState gameId={gameId} />
                ) : (
                  <PannableMapView gameId={gameId} />
                )}
              </TabActiveContext>
            </Tabs.Panel>

            <TabPanelSection
              value="player"
              className={classes.playersTabContent}
              visited={visitedTabs.has("player")}
            >
              <TabContent
                gameId={gameId}
                ready={!!data?.playerData}
                isError={isError}
              >
                <PlayerTab />
              </TabContent>
            </TabPanelSection>

            <TabPanelSection
              value="players"
              className={classes.playersTabContent}
              visited={visitedTabs.has("players")}
            >
              <TabContent
                gameId={gameId}
                ready={!!data?.playerData}
                isError={isError}
              >
                <PlayersTab playerData={data?.playerData ?? []} />
              </TabContent>
            </TabPanelSection>

            <TabPanelSection
              value="objectives"
              className={classes.playersTabContent}
              visited={visitedTabs.has("objectives")}
            >
              <TabContent gameId={gameId} ready={!!data} isError={isError}>
                <ScoreBoard />
              </TabContent>
            </TabPanelSection>

            <TabPanelSection
              value="general"
              className={classes.playersTabContent}
              visited={visitedTabs.has("general")}
            >
              <TabContent gameId={gameId} ready={!!data} isError={isError}>
                <GeneralArea />
              </TabContent>
            </TabPanelSection>
          </Tabs>
        </Box>
      </AppShell.Main>

      <SettingsModal
        opened={settings.settingsModalOpened}
        onClose={() => handlers.setSettingsModalOpened(false)}
        gameId={gameId}
      />

      <SystemDossierModal />
      <MoveUnitsModal />
      <MoveQuantityModal />
      <MultiSelectHud />
      <LoadTransportModal />
      <CombatModal />
      {/* Okno POLA BITWY — pełny ekran, samo pojawia się, gdy trwa walka (RULES.md 39). */}
      {/* Okno INWAZJI (RULES.md 40) — pod polem bitwy, żeby walka naziemna otwierała się nad nim. */}
      {/* Okno PRODUKCJI (RULES.md 33.3) — otwiera się samo w kroku PRODUCTION, pod inwazją. */}
      <ProductionOverlay />
      {/* Okno RADY GALAKTYCZNEJ (RULES.md 51) - faza agendy: ujawnienie, głosowanie, wynik. */}
      <AgendaOverlay />
      <InvasionOverlay />
      {/* Okno EKSPLORACJI (RULES.md 46) - po Establish Control, nad oknem inwazji. */}
      <ExplorationOverlay />
      {/* Thunder's Edge (RULES.md 50): rzut na The Fracture, żetony ingress, Thunder's Edge. */}
      <ThundersEdgeOverlay />
      {/* Setup startowy (RULES.md 45): tajne cele, żeton Custodians, odkrycie celów —
          pełny ekran do domknięcia setupu, zanim ruszy faza strategii. */}
      <GameSetupOverlay />
      <BattleOverlay />
      {/* Wspólna scena kości (RULES.md / docs: dice) - Space Cannon, bombardowanie, Fracture,
          karty akcji. Pole bitwy ma własny stół. */}
      <DiceStageHost />
      <TableRollWatcher />
      {/* Wszystkie komunikaty w jednym miejscu (u góry na środku): odrzucone akcje
          i powiadomienia „kto co zrobił" z feedu Activity; same znikają. */}
      <NotificationArea />
      {/* Dźwięk: kliknięcia UI, muzyka tła wg nastroju, kwestie frakcji z feedu Activity. */}
      <AudioDirector />
      {/* Odsłonięcie reliktu (fragmenty, The Fracture) - scena u wszystkich (RULES.md 59.8). */}
      <RelicRevealWatcher />
      {/* Limit pojemności (RULES.md 39.6) — modal nad mapą i nad polem bitwy, sam się pokazuje
          przy oknie CAPACITY (myśliwce, piechota, mechy w przestrzeni ponad capacity). */}
      <CapacityModal />
      {/* Fleet pool (RULES.md 42) - statki ponad pulę floty trzeba zwrócić do rezerwy. */}
      <FleetPoolModal />
      {/* Popup decyzji „follow / don't follow" secondary karty strategii — pyta
          bieżącego respondenta okna STRATEGY_SECONDARY (RULES.md 29.2, 31.6). */}
      <SecondaryDecisionModal />
      {/* Decyzje graczy (RULES.md 56): technologie/zdolności z „may" i wybory celu - gracz zawsze
          decyduje sam, silnik nigdy nie wybiera za niego. */}
      {/* Jedno centrum decyzji: oferty, transakcje, okna kart z ręki, „Available now”. */}
      <DecisionCenter />
      {/* Efekty trwałe „obok planszy” (bohaterowie, kości agentów, premie z kart) - RULES.md 54. */}
      {onMapTab && <ActiveEffectsPanel />}

      {/* Koniec gry: zwycięzca → głosowanie (honor) → Kronika epilogu → podsumowanie.
          Pojawia się natychmiast, gdy backend ustawi `winnerId` (próg VP / koniec rund). */}
      <VictoryScreen />

      <KeyboardShortcutsModal
        opened={settings.keyboardShortcutsModalOpened}
        onClose={() => handlers.setKeyboardShortcutsModalOpened(false)}
      />

      <NavigationDrawer
        opened={drawerOpened}
        onClose={() => setDrawerOpened(false)}
        activeTab={activeTab}
        onTabChange={changeActiveTab}
        gameId={gameId}
        activeTabs={activeTabs}
        onGameChange={changeTab}
        onRemoveTab={removeTab}
        onCardsClick={mobileOpenHand}
        onEventsClick={mobileOpenEvents}
      />

      {canViewSecretHand && (
        <MobileHandSheet
          gameId={gameId}
          opened={handOpened}
          onClose={() => setHandOpened(false)}
        />
      )}

      <MobileEventsSheet
        opened={eventsOpened}
        onClose={() => setEventsOpened(false)}
      />
    </AppShell>
  );
}

function GameMapPage() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const themeClassName = usePageThemeClass({ mobile: isMobileDevice() });
  // Układ „panels" (MapView) jest wyłączony — używamy WYŁĄCZNIE pannable
  // (decyzja użytkownika). Brak wyboru = brak modala selekcji.
  return (
    <GameContextProvider gameId={gameId}>
      <div className={themeClassName}>
        <GameMapContent />
        {/* Gra sieciowa (RULES.md 44.2): plakietka „kim jestem", zaproszenia hosta, push stanu. */}
        <NetworkPanel />
      </div>
    </GameContextProvider>
  );
}

export default GameMapPage;
