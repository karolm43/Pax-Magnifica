import { useEffect, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { Button, Group, Stack, Text } from "@/ds";
import {
  IconAlertTriangle,
  IconCheck,
  IconMinus,
  IconPlus,
  IconRotate,
  IconWand,
} from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useCapacity } from "@/api/useBoardEditor";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { Unit } from "@/shared/ui/Unit";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { excessFor, remainingCargo, removalStatus } from "./capacityMath";
import styles from "./CapacityModal.module.css";

/**
 * Okno LIMITU POJEMNOŚCI (RULES.md 39.6) — „masz w przestrzeni więcej ładunku, niż zmieszczą
 * twoje statki".
 *
 * Silnik otwiera okno ``CAPACITY`` po wyłonieniu zwycięzcy walki kosmicznej i przed przejściem
 * kroku akcji (np. gdy Space Cannon zniszczył carrier). Modal adresuje BIEŻĄCEGO respondenta
 * (hot-seat: gracze po kolei) i jest NIEODRZUCALNY — nadwyżkę trzeba usunąć, zanim akcja pójdzie
 * dalej. Działa niezależnie od okna bitwy (z-index modali > pole bitwy), bo dotyczy też piechoty
 * i mechów w przestrzeni, a nie tylko walki.
 *
 * Wybór: +/- na każdym typie (myśliwce, piechota, mechy), „Auto" = podpowiedź silnika
 * (najtańsze najpierw), pasek ładowni na żywo pokazuje miejsca statków, przydział doku dla
 * myśliwców i przepełnienie. Poprawność liczy ``capacityMath`` (ta sama formuła co backend).
 */
export function CapacityModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { capacityResolve } = useBoardEditor();
  const window = gameState?.pendingWindow ?? null;
  const pending =
    !!window && window.windowType === "CAPACITY" && !window.isComplete;
  const { data: view } = useCapacity(pending);
  const [remove, setRemove] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  // Nowy respondent / nowe okno → zacznij od podpowiedzi silnika.
  const viewKey = view?.active
    ? `${view.playerId}@${view.position}:${view.used}`
    : null;
  useEffect(() => {
    // Podpowiedź ładujemy tylko przy zmianie okna/respondenta (viewKey), nie przy każdym odczycie.
    if (viewKey && view) setRemove({ ...view.suggestion });
  }, [viewKey]);

  if (!pending || !view?.active) return null;

  const player = gameData?.playerData?.find((p) => p.faction === view.player);
  const name = player
    ? getPlayerFactionDisplayName(player)
    : (view.player ?? "");
  const colorAlias = getColorAlias(player?.color);
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName =
    (tile ? getTileById(tile.systemId)?.name : undefined) ??
    view.position ??
    "";

  const left = remainingCargo(view, remove);
  const status = removalStatus(view, remove);
  const overBy = excessFor(view, left);
  const removedTotal = Object.values(remove).reduce((a, b) => a + b, 0);

  // Pasek ładowni: miejsca doku (tylko myśliwce) + miejsca statków; wypełnienie = co zostaje.
  const costOf = (bt: string) =>
    view.cargo.find((c) => c.baseType === bt)?.cost ?? 1;
  const fighterLoad = costOf("fighter") * (left.fighter ?? 0);
  const dockUsed = Math.min(fighterLoad, view.fighterOnly);
  const shipLoad =
    Object.entries(left).reduce((s, [bt, n]) => s + costOf(bt) * n, 0) -
    dockUsed;
  const shipUsed = Math.min(shipLoad, view.general);
  const overflow = Math.max(0, shipLoad - view.general);
  const cells = [
    ...Array.from({ length: view.fighterOnly }, (_, i) => ({
      kind: "dock" as const,
      full: i < dockUsed,
    })),
    ...Array.from({ length: view.general }, (_, i) => ({
      kind: "ship" as const,
      full: i < shipUsed,
    })),
    ...Array.from({ length: overflow }, () => ({
      kind: "over" as const,
      full: true,
    })),
  ];

  const step = (bt: string, max: number, delta: number) =>
    setRemove((prev) => ({
      ...prev,
      [bt]: Math.max(0, Math.min(max, (prev[bt] ?? 0) + delta)),
    }));

  const confirm = () => {
    if (busy || status !== "exact" || !view.player) return;
    setBusy(true);
    void capacityResolve(view.player, remove).finally(() => setBusy(false));
  };

  return (
    <AppModal
      opened
      // Wymuszone: nadwyżkę trzeba usunąć (RULES.md 39.6 C2) — modal znika, gdy silnik zamknie okno.
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      title="Capacity exceeded"
      size={520}
    >
      <Stack gap="md">
        <Group gap="sm" wrap="nowrap">
          {player?.faction ? (
            <CircularFactionIcon faction={player.faction} size={34} />
          ) : null}
          <Stack gap={2} style={{ minWidth: 0 }}>
            <Text size="xs" c="dimmed">
              Your call · {systemName}
              {view.position && systemName !== view.position
                ? ` (${view.position})`
                : ""}
            </Text>
            <Text fw={700}>{name}</Text>
          </Stack>
        </Group>

        <Text size="sm">
          Your ships can't carry all fighters and ground forces in this system's
          space. Choose which units return to your reinforcements. Ground forces
          on planets don't count.
        </Text>

        {/* Ładownia: dok (myśliwce) + statki, przepełnienie na czerwono. */}
        <div className={styles.hold} aria-label="Cargo hold">
          <div className={styles.holdHead}>
            <span>Hold</span>
            <span>
              {shipUsed + dockUsed + overflow} /{" "}
              {view.general + view.fighterOnly}
              {view.fighterOnly > 0 && (
                <small> · {view.fighterOnly} dock slots for fighters</small>
              )}
            </span>
          </div>
          <div className={styles.cells} data-over={overflow > 0 || undefined}>
            {cells.length === 0 && (
              <span className={styles.noCells}>No capacity</span>
            )}
            {cells.map((cell, i) => (
              <span
                key={i}
                className={styles.cell}
                data-kind={cell.kind}
                data-full={cell.full || undefined}
                style={{ "--i": i } as CSSProperties}
              />
            ))}
          </div>
        </div>

        <Stack gap={8}>
          {view.cargo.map((c) => {
            const n = remove[c.baseType] ?? 0;
            return (
              <div key={c.baseType} className={styles.row}>
                <div className={styles.sprite}>
                  <Unit
                    unitType={c.asyncId}
                    colorAlias={colorAlias}
                    faction={player?.faction}
                    scaleSprite
                  />
                </div>
                <div className={styles.rowInfo}>
                  <b>{c.name}</b>
                  <span className={styles.tokens} aria-hidden="true">
                    {Array.from({ length: c.count }, (_, i) => (
                      <span
                        key={i}
                        className={styles.token}
                        data-removed={i >= c.count - n || undefined}
                      />
                    ))}
                  </span>
                  <small>
                    {c.count} in space · keep {c.count - n}
                    {n > 0 ? ` · remove ${n}` : ""}
                  </small>
                </div>
                <div className={styles.stepper}>
                  <button
                    type="button"
                    disabled={busy || n <= 0}
                    onClick={() => step(c.baseType, c.count, -1)}
                    aria-label={`Keep one more ${c.name}`}
                  >
                    <IconMinus size={14} />
                  </button>
                  <span
                    className={styles.stepValue}
                    data-active={n > 0 || undefined}
                  >
                    {n}
                  </span>
                  <button
                    type="button"
                    disabled={busy || n >= c.count}
                    onClick={() => step(c.baseType, c.count, +1)}
                    aria-label={`Remove one ${c.name}`}
                  >
                    <IconPlus size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </Stack>

        <div className={styles.status} data-status={status} role="status">
          {status === "over" && (
            <>
              <IconAlertTriangle size={15} aria-hidden="true" /> Still over
              capacity by {overBy} — remove more.
            </>
          )}
          {status === "tooMany" && (
            <>
              <IconAlertTriangle size={15} aria-hidden="true" /> You're removing
              more than needed — keep some back.
            </>
          )}
          {status === "exact" && (
            <>
              <IconCheck size={15} aria-hidden="true" /> Fits. {removedTotal}{" "}
              unit
              {removedTotal === 1 ? "" : "s"} return to reinforcements.
            </>
          )}
        </div>

        <Group justify="space-between" gap="xs">
          <Group gap="xs">
            <Button
              size="xs"
              variant="default"
              leftSection={<IconWand size={14} />}
              disabled={busy}
              onClick={() => setRemove({ ...view.suggestion })}
            >
              Auto
            </Button>
            <Button
              size="xs"
              variant="default"
              leftSection={<IconRotate size={14} />}
              disabled={busy || removedTotal === 0}
              onClick={() => setRemove({})}
            >
              Reset
            </Button>
          </Group>
          <Button
            leftSection={<IconCheck size={16} />}
            disabled={status !== "exact"}
            loading={busy}
            onClick={confirm}
          >
            Remove {removedTotal} unit{removedTotal === 1 ? "" : "s"}
          </Button>
        </Group>

        {view.remaining > 1 && (
          <Text size="xs" c="dimmed">
            {view.remaining - 1} more player
            {view.remaining - 1 === 1 ? "" : "s"} must check capacity after you.
          </Text>
        )}
      </Stack>
    </AppModal>
  );
}

export default CapacityModal;
