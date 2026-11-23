import { useBoardEditor } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import {
  useFactionComponentForm,
  type FactionComponentKind,
} from "@/api/useFactionComponents";
import type { ComponentRef } from "@/domains/cards/components/ComponentInfo";
import { ComponentUseModal, formError } from "./ComponentUseModal";

type Props = {
  kind: FactionComponentKind;
  componentId: string;
  name: string;
  /** Gracz-właściciel komponentu. */
  playerId: string;
  onClose: () => void;
  onDone: () => void;
};

const STATUS_COPY: Record<string, string> = {
  locked: "Locked",
  unlocked: "Ready",
  exhausted: "Exhausted",
  purged: "Purged",
};

const KIND_LABEL: Record<FactionComponentKind, string> = {
  leader: "Leader",
  ability: "Faction ability",
  breakthrough: "Breakthrough",
  technology: "Faction technology",
};

/** Odnośnik do pełnej karty (ⓘ) - tylko rodzaje, które mają kartę w `ComponentInfo`. */
function infoRefOf(kind: FactionComponentKind, id: string): ComponentRef | undefined {
  if (kind === "leader") return { kind: "leader", id };
  if (kind === "breakthrough") return { kind: "breakthrough", id };
  if (kind === "technology") return { kind: "tech", id };
  return undefined;
}

/**
 * Lider / zdolność frakcji / przełom (RULES.md 61.1, 61.3). Formularz z opisu silnika
 * (`/faction-component/{kind}/{id}/form`). „ACTION:" zagrywa się jako akcja tury, koszt (wyczerpanie
 * agenta, purge bohatera, wyczerpanie przełomu) płaci silnik. Zablokowany lider bez sprawdzanego
 * warunku ma przycisk ręcznego odblokowania; reszta odblokowuje się sama.
 */
export function FactionComponentUseModal({
  kind,
  componentId,
  name,
  playerId,
  onClose,
  onDone,
}: Props) {
  const form = useFactionComponentForm(kind, componentId, playerId);
  const { playFactionComponent, claimLeaderUnlock } = useBoardEditor();
  const setNotice = useAppStore((state) => state.setNotice);
  const data = form.data;
  const status = data?.status ?? "";
  const notReady = kind !== "ability" && status !== "" && status !== "unlocked";
  // ACTION (akcja tury) albo „During X: you may…" (bez akcji tury) — oba z formularzem silnika.
  const isAction = data?.mode === "action" || data?.mode === "window";
  const isWindow = data?.mode === "window";

  const notes: string[] = [];
  if (data) {
    if (status) {
      notes.push(`${STATUS_COPY[status] ?? status}${data.leader_type ? ` ${data.leader_type}` : ""}`);
    }
    if (status === "locked" && data.unlock_condition) {
      notes.push(
        `Unlock: ${data.unlock_condition}${
          data.can_claim_unlock
            ? " The engine does not check this condition yet - unlock it yourself when you meet it."
            : " It unlocks automatically when you meet it."
        }`,
      );
    }
    if (isWindow) {
      notes.push("Use it at the moment the card describes - it does not take your action.");
    }
    if (isAction && !data.implemented) {
      notes.push("The engine does not automate this ability yet. Resolve the effect by hand.");
    }
    if (!isAction) {
      notes.push(
        data.implemented
          ? "This ability works on its own - the engine asks you at the right moment."
          : "This ability is not automated yet - resolve it by hand when it applies.",
      );
    }
  }

  return (
    <ComponentUseModal
      title={name}
      kind={KIND_LABEL[kind]}
      infoRef={infoRefOf(kind, componentId)}
      infoName={name}
      loading={form.isLoading}
      error={formError(form.error, "Could not load this component.")}
      text={data?.text}
      notes={notes}
      inputs={data?.inputs ?? []}
      showForm={isAction && !notReady}
      useLabel={isAction ? "Use ability" : undefined}
      cancelLabel={isAction ? "Cancel" : "Close"}
      blocked={notReady}
      onUse={
        isAction
          ? async (params) => {
              const result = await playFactionComponent(playerId, kind, componentId, params);
              if (!result.implemented) {
                setNotice(
                  isWindow
                    ? `${name} is not automated yet - resolve its effect by hand.`
                    : `${name} is not automated yet - it counts as your action. Resolve its effect by hand.`,
                  "info",
                );
              }
              onDone();
            }
          : undefined
      }
      secondary={
        data?.can_claim_unlock
          ? {
              label: "Unlock",
              run: async () => {
                await claimLeaderUnlock(playerId, componentId);
                onDone();
              },
            }
          : undefined
      }
      onClose={onClose}
    />
  );
}
