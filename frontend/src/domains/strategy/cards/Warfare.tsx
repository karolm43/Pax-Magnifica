import { useEffect, useState } from "react";
import { IconCheck, IconTarget } from "@tabler/icons-react";
import { useAppStore } from "@/state/appStore";
import { ConfirmButton, Hint, PoolDistributor, PromptShell } from "../PromptParts";
import { num, type PoolSplit } from "../strategyPrompt";
import type { PrimaryViewProps } from "./types";

/*
 * Warfare, wersja Thunder's Edge (RULES.md 30.11): primary - redystrybucja żetonów, akcja
 * taktyczna w dowolnym systemie BEZ żetonu, redystrybucja po akcji. Secondary (PRODUCTION
 * w home system) otwiera zwykłe okno produkcji, więc nie ma osobnego widoku wyborów.
 *
 * Kroki `activate_system` i `tactical_action` są pokazywane jako NIEBLOKUJĄCY dok (mapa i
 * panel akcji taktycznej muszą pozostać klikalne), pozostałe - jako okno modalne.
 */

export function WarfarePrimary(props: PrimaryViewProps) {
  const step = props.prompt.step;
  if (step === "activate_system") return <ActivateDock {...props} />;
  if (step === "tactical_action") return <TacticalDock {...props} />;
  return <Redistribute {...props} after={step === "redistribute_after"} />;
}

function Redistribute({
  prompt,
  shell,
  owner,
  busy,
  submit,
  after,
}: PrimaryViewProps & { after: boolean }) {
  const o = prompt.options;
  const total = num(o.total);
  const initial: PoolSplit = {
    tactical: num(o.tactical),
    fleet: num(o.fleet),
    strategic: num(o.strategic),
  };
  const [split, setSplit] = useState<PoolSplit>(initial);
  const placed = split.tactical + split.fleet + split.strategic;
  const changed =
    split.tactical !== initial.tactical ||
    split.fleet !== initial.fleet ||
    split.strategic !== initial.strategic;
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle={after ? "Redistribute after the action" : "Redistribute before the action"}
      footer={
        <ConfirmButton
          disabled={busy || (changed && placed !== total)}
          icon={<IconCheck size={16} />}
          onClick={() => submit(changed ? { ...split } : {})}
        >
          {changed ? "Apply" : "Keep as is"}
        </ConfirmButton>
      }
    >
      <Hint>
        You may <b>redistribute your command tokens</b> between your pools{" "}
        {after ? "after" : "before"} the free tactical action. Total tokens: <b>{total}</b>.
      </Hint>
      <PoolDistributor total={total} value={split} onChange={setSplit} player={owner} busy={busy} />
    </PromptShell>
  );
}

/** Włącza tryb "wskaż system na mapie" na czas kroku; klik obsługuje TurnControls. */
function ActivateDock({ shell }: PrimaryViewProps) {
  const activateMode = useAppStore((s) => s.activateMode);
  const toggleActivateMode = useAppStore((s) => s.toggleActivateMode);
  useEffect(() => {
    if (!useAppStore.getState().activateMode) toggleActivateMode();
    return () => {
      if (useAppStore.getState().activateMode) toggleActivateMode();
    };
  }, [toggleActivateMode]);
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Tactical action - no command token"
    >
      <Hint>
        <IconTarget size={14} aria-hidden="true" /> Click <b>any system on the map</b> to activate
        it. No command token is placed (even if yours is already there) and the tactical pool is
        not spent.
        {activateMode ? "" : " (Picking mode is starting...)"}
      </Hint>
    </PromptShell>
  );
}

function TacticalDock({ shell }: PrimaryViewProps) {
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Resolve the tactical action"
    >
      <Hint>
        Move, fight, invade and produce as usual. When you are done, press <b>End action</b> to
        continue with the last token redistribution.
      </Hint>
    </PromptShell>
  );
}
