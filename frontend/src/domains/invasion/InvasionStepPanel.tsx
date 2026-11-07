import { useState } from "react";
import { useParams } from "react-router-dom";
import { IconFlag, IconMinus, IconPlus, IconRocket } from "@tabler/icons-react";
import { DEFAULT_GAME_ID } from "@/config";
import { fetchJson } from "@/api/fetchJson";
import { useGameState } from "@/api/useGameState";
import { useAppStore } from "@/state/appStore";
import { getPlanetData } from "@/entities/lookup/planets";
import {
  bumpStage,
  landAll,
  remainingOf,
  stageList,
  stageTotal,
  type Stage,
} from "./invasionStage";
import {
  useInvasion,
  useInvasionActions,
  type InvasionView,
} from "./useInvasion";
import styles from "./InvasionStepPanel.module.css";

const OUTCOME: Record<string, string> = {
  captured: "captured",
  retained: "kept by the defender",
  lost: "not taken",
  already_controlled: "already yours",
};

/**
 * Krok INVASION w panelu pomocy (RULES.md 40). Inwazja startuje PRZYCISKIEM. Gdy nie ma
 * wrogich sił, struktur z Space Cannon ani celu bombardowania (kroki 1, 3, 4 odpadają), całe
 * lądowanie to prosty wybór „ile piechoty / mechów gdzie"; w przeciwnym razie otwiera się
 * pełne okno inwazji (`InvasionOverlay`).
 */
export function InvasionStepPanel() {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const setNotice = useAppStore((s) => s.setNotice);
  const active = gameState?.activeInvasion != null;
  const { data: view } = useInvasion(active);
  const actions = useInvasionActions();
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<Stage>({});

  const run = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch {
      // Powód (422) trafia do panelu komunikatów (post() → notice).
    } finally {
      setBusy(false);
    }
  };

  if (gameState?.activeCombat) {
    return <span className={styles.note}>Ground combat in progress.</span>;
  }

  if (!active || !view?.active) {
    return (
      <div className={styles.box}>
        <button
          type="button"
          className={styles.primary}
          disabled={busy}
          onClick={() => void run(actions.begin)}
        >
          <IconRocket size={14} aria-hidden="true" /> Start invasion
        </button>
        <span className={styles.note}>
          Land ground forces from orbit. Bombardment, Space Cannon and ground
          combat open only when someone defends.
        </span>
      </div>
    );
  }

  if (!view.simple) {
    return (
      <span className={styles.note}>
        Invasion window is open (step {view.phase?.toLowerCase()}). Use
        &quot;Hide&quot; there to look at the map.
      </span>
    );
  }

  const landing = async () => {
    if (stageTotal(stage) > 0) await actions.commit(stageList(stage));
    await actions.next(); // → Establish Control (kroki 3–4 pominięte automatycznie)
    const after = await fetchJson<InvasionView>(
      "/bot/tactical/invasion",
      "invasion",
    );
    const text = after.results
      .map(
        (r) => `${getPlanetData(r.planet)?.name ?? r.planet}: ${OUTCOME[r.outcome]}`,
      )
      .join(" · ");
    setStage({});
    // Przejęcie niczyjej planety otwiera okno eksploracji (RULES.md 46): inwazję zamknie dopiero
    // przycisk poniżej, po rozstrzygnięciu kart.
    if (after.results.some((r) => r.explore)) {
      setNotice(`${text} · explore the captured planets`, "info");
      return;
    }
    await actions.next(); // zamknięcie inwazji
    setNotice(text || "No landing.", "info");
  };

  // Lądowanie zrobione (Establish Control), czeka tylko na eksplorację / zamknięcie.
  if (view.phase === "ESTABLISH") {
    const exploring = gameState?.activeExploration != null;
    return (
      <div className={styles.box}>
        <span className={styles.note}>
          {exploring
            ? "Resolve the exploration cards to continue."
            : "Control is settled."}
        </span>
        <button
          type="button"
          className={styles.primary}
          disabled={busy || exploring}
          onClick={() => void run(actions.next)}
        >
          <IconFlag size={14} aria-hidden="true" /> Close invasion
        </button>
      </div>
    );
  }

  const total = stageTotal(stage);
  return (
    <div className={styles.box}>
      {view.cargo.length === 0 && (
        <span className={styles.note}>No ground forces in orbit.</span>
      )}
      {view.planets.map((p) => {
        const name = getPlanetData(p.planet)?.name ?? p.planet;
        const staged = stage[p.planet] ?? {};
        return (
          <div className={styles.planet} key={p.planet}>
            <div className={styles.head}>
              <b>{name}</b>
              <small>
                {p.owner ? "controlled" : "uncontrolled"}
                {Object.values(p.structures).flat().length > 0 &&
                  ` · ${Object.values(p.structures)
                    .flat()
                    .map((s) => `${s.count}× ${s.name}`)
                    .join(", ")}`}
              </small>
            </div>
            {view.cargo.map((u) => (
              <div className={styles.step} key={u.baseType}>
                <span>{u.name}</span>
                <button
                  type="button"
                  className={styles.stepBtn}
                  aria-label={`Fewer ${u.name} on ${name}`}
                  disabled={(staged[u.baseType] ?? 0) === 0}
                  onClick={() =>
                    setStage((s) => bumpStage(s, view.cargo, p.planet, u.baseType, -1))
                  }
                >
                  <IconMinus size={16} />
                </button>
                <b>{staged[u.baseType] ?? 0}</b>
                <button
                  type="button"
                  className={styles.stepBtn}
                  aria-label={`More ${u.name} on ${name}`}
                  disabled={remainingOf(view.cargo, stage, u.baseType) === 0}
                  onClick={() =>
                    setStage((s) => bumpStage(s, view.cargo, p.planet, u.baseType, 1))
                  }
                >
                  <IconPlus size={16} />
                </button>
              </div>
            ))}
            {view.cargo.length > 0 && (
              <button
                type="button"
                className={styles.ghost}
                onClick={() => setStage((s) => landAll(s, view.cargo, p.planet))}
              >
                All here
              </button>
            )}
          </div>
        );
      })}
      <button
        type="button"
        className={styles.primary}
        disabled={busy}
        onClick={() => void run(landing)}
      >
        <IconFlag size={14} aria-hidden="true" />{" "}
        {total > 0 ? `Land ${total} and take control` : "Finish without landing"}
      </button>
    </div>
  );
}
