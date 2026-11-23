import { useState } from "react";
import { IconCheck, IconTarget } from "@tabler/icons-react";
import { ConfirmButton, Hint, PoolDistributor, PromptShell } from "../PromptParts";
import { useMapPick } from "../mapPick";
import { num, strList, type PoolSplit } from "../strategyPrompt";
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
      <PoolDistributor total={total} value={split} onChange={setSplit} player={owner} busy={busy} auto={initial} />
    </PromptShell>
  );
}

/**
 * Wybór systemu do darmowej akcji taktycznej: wszystkie systemy świecą na mapie, klik od
 * razu aktywuje (jak zwykła aktywacja), ale przez krok karty - bez żetonu i bez puli.
 * Nie używamy trybu aktywacji z TurnControls: tamten wywołuje zwykłą aktywację, którą
 * silnik odrzuca („already took an action"), bo akcją tej tury jest już Warfare.
 */
function ActivateDock({ prompt, shell, busy, submit }: PrimaryViewProps) {
  const systems = strList(prompt.options.systems);
  useMapPick("system", systems, (position) => submit({ system: position }), {
    hue: shell.hue,
    enabled: !busy,
  });
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Tactical action - no command token"
    >
      <Hint>
        <IconTarget size={14} aria-hidden="true" /> <b>Click any system on the map</b> to
        activate it. No command token is placed (even if yours is already there) and your
        tactic pool is not spent.
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
