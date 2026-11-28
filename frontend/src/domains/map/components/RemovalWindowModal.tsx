import { useEffect, useState, type ReactNode } from "react";
import { Button, Group, Stack, Text } from "@/ds";
import {
  IconAlertTriangle,
  IconCheck,
  IconRotate,
} from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { Stepper } from "@/shared/ui/Stepper/Stepper";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { Unit } from "@/shared/ui/Unit";
import { useAppStore } from "@/state/appStore";
import { getColorAlias } from "@/entities/lookup/colors";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import styles from "./CapacityModal.module.css";

/** Jedna pozycja do usunięcia (statek albo ładunek). */
export type RemovalItem = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
};

export type RemovalStatus = "over" | "tooMany" | "exact";

export type RemovalEvaluation = {
  status: RemovalStatus;
  /** Tekst dla stanu „za mało usunięto" (np. „Remove 2 more ships."). */
  overText: string;
  /** Tekst dla stanu „dokładnie tyle, ile trzeba". */
  exactText: string;
};

type Props = {
  title: string;
  /** Klucz okna/respondenta: zmiana resetuje wybór do podpowiedzi silnika. */
  viewKey: string | null;
  player: PlayerData | undefined;
  /** Nazwa gracza, gdy brak danych frakcji. */
  fallbackName: string;
  systemName: string;
  position: string | null;
  /** Opis reguły: dlaczego okno się pojawiło i co wolno wybrać. */
  intro: ReactNode;
  /** Dodatkowy element nad listą (pasek ładowni, aktywne technologie) - zna aktualny wybór. */
  extra?: (remove: Record<string, number>) => ReactNode;
  items: RemovalItem[];
  /** „in space" / „in system" - gdzie stoją jednostki. */
  locationNoun: string;
  /** „unit" / „ship" - rzeczownik w przyciskach i komunikatach. */
  unitNoun: string;
  evaluate: (remove: Record<string, number>) => RemovalEvaluation;
  /** Ilu graczy jeszcze sprawdza limit (łącznie z bieżącym) + nazwa limitu do stopki. */
  remaining: number;
  checkNoun: string;
  onConfirm: (remove: Record<string, number>) => Promise<void>;
};

/**
 * Wspólne okno usuwania nadwyżki ponad limit: pojemność (RULES.md 39.6) i pula floty (42).
 *
 * Oba okna mają ten sam przebieg: respondent wybiera +/- ile sztuk wraca do rezerwy (zawsze
 * ręcznie, bez „Auto" - decyzja użytkownika 2026-11-27), a zatwierdzić można dopiero dokładną liczbę.
 * Okno jest NIEODRZUCALNE (silnik zamyka je sam). Powód odmowy serwera (422) widać TUTAJ,
 * w oknie, bo modal przykrywa panel komunikatów na mapie.
 */
export function RemovalWindowModal({
  title,
  viewKey,
  player,
  fallbackName,
  systemName,
  position,
  intro,
  extra,
  items,
  locationNoun,
  unitNoun,
  evaluate,
  remaining,
  checkNoun,
  onConfirm,
}: Props) {
  const [remove, setRemove] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const notice = useAppStore((s) => s.notice);
  const clearNotice = useAppStore((s) => s.clearNotice);

  // Nowy respondent / nowe okno -> zacznij od pustego wyboru (nie przy każdym odczycie).
  useEffect(() => {
    if (viewKey) {
      setRemove({});
      clearNotice();
    }
  }, [viewKey]);

  const name = player ? getPlayerFactionDisplayName(player) : fallbackName;
  const colorAlias = getColorAlias(player?.color);
  const removedTotal = Object.values(remove).reduce((a, b) => a + b, 0);
  const verdict = evaluate(remove);
  const plural = (n: number) => (n === 1 ? "" : "s");

  const step = (bt: string, max: number, delta: number) =>
    setRemove((prev) => ({
      ...prev,
      [bt]: Math.max(0, Math.min(max, (prev[bt] ?? 0) + delta)),
    }));

  const confirm = () => {
    if (busy || verdict.status !== "exact") return;
    setBusy(true);
    // Błąd serwera trafia do ``notice`` (post -> setNotice) i jest pokazany niżej w oknie.
    onConfirm(remove)
      .catch(() => undefined)
      .finally(() => setBusy(false));
  };

  return (
    <AppModal
      floating
      minimizable
      opened
      // Wymuszone: nadwyżkę trzeba usunąć - modal znika, gdy silnik zamknie okno.
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      title={title}
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
              {position && systemName !== position ? ` (${position})` : ""}
            </Text>
            <Text fw={700}>{name}</Text>
          </Stack>
        </Group>

        <Text size="sm">{intro}</Text>
        {extra?.(remove)}

        <Stack gap={8}>
          {items.map((c) => {
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
                    {c.count} {locationNoun} · keep {c.count - n}
                    {n > 0 ? ` · remove ${n}` : ""}
                  </small>
                </div>
                <Stepper
                  bare
                  active
                  label={`${c.name} to remove`}
                  value={n}
                  max={c.count}
                  disabled={busy}
                  onChange={(next) => step(c.baseType, c.count, next - n)}
                />
              </div>
            );
          })}
        </Stack>

        <div
          className={styles.status}
          data-status={verdict.status}
          role="status"
        >
          {verdict.status === "over" && (
            <>
              <IconAlertTriangle size={15} aria-hidden="true" />{" "}
              {verdict.overText}
            </>
          )}
          {verdict.status === "tooMany" && (
            <>
              <IconAlertTriangle size={15} aria-hidden="true" /> You're removing
              more than needed - keep some back.
            </>
          )}
          {verdict.status === "exact" && (
            <>
              <IconCheck size={15} aria-hidden="true" /> {verdict.exactText}
            </>
          )}
        </div>

        {/* Powód odmowy serwera (422) - modal przykrywa panel komunikatów, więc pokazujemy go tu. */}
        {notice?.kind === "error" && (
          <div className={styles.status} data-status="over" role="alert">
            <IconAlertTriangle size={15} aria-hidden="true" /> {notice.text}
          </div>
        )}

        <Group justify="space-between" gap="xs">
          <Group gap="xs">
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
            disabled={verdict.status !== "exact"}
            loading={busy}
            onClick={confirm}
          >
            Remove {removedTotal} {unitNoun}
            {plural(removedTotal)}
          </Button>
        </Group>

        {remaining > 1 && (
          <Text size="xs" c="dimmed">
            {remaining - 1} more player{plural(remaining - 1)} must check{" "}
            {checkNoun} after you.
          </Text>
        )}
      </Stack>
    </AppModal>
  );
}

export default RemovalWindowModal;
