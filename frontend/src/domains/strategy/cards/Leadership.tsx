import { useState } from "react";
import { IconArrowLeft, IconCheck } from "@tabler/icons-react";
import { Button } from "@/ds";
import {
  ConfirmButton,
  Hint,
  PaymentPicker,
  PoolDistributor,
  PromptShell,
  paymentTotal,
  type Payment,
} from "../PromptParts";
import { EMPTY_SPLIT, num, numberMap, type PoolSplit } from "../strategyPrompt";
import type { PrimaryViewProps, SecondaryViewProps } from "./types";

/*
 * Leadership (RULES.md 30.7): zdobądź 3 żetony, potem opcjonalnie wydaj wpływ
 * (1 żeton za 3 wpływu); secondary - to samo bez 3 żetonów i bez żetonu strategii.
 */

const NO_PAYMENT: Payment = { planets: [], tradeGoods: 0 };

function useInfluencePlan(options: Record<string, unknown>, baseGain: number) {
  const values = numberMap(options.planets);
  const perToken = num(options.per_token) || 3;
  const reinforcements = num(options.reinforcements);
  const [payment, setPayment] = useState<Payment>(NO_PAYMENT);
  const paid = paymentTotal(values, payment);
  const bought = Math.floor(paid / perToken);
  const gain = Math.min(baseGain + bought, reinforcements);
  return { values, perToken, reinforcements, payment, setPayment, paid, bought, gain };
}

export function LeadershipPrimary(props: PrimaryViewProps) {
  const { prompt, shell, busy, submit } = props;
  if (prompt.step === "distribute") {
    return <DistributeStep {...props} total={num(prompt.draft.gain)} />;
  }
  return <SpendStep prompt={prompt} shell={shell} busy={busy} submit={submit} />;
}

function SpendStep({
  prompt,
  shell,
  busy,
  submit,
}: Pick<PrimaryViewProps, "prompt" | "shell" | "busy" | "submit">) {
  const o = prompt.options;
  const plan = useInfluencePlan(o, num(o.base_gain));
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Gain command tokens"
      footer={
        <ConfirmButton
          disabled={busy}
          icon={<IconCheck size={16} />}
          onClick={() =>
            submit({ planets: plan.payment.planets, trade_goods: plan.payment.tradeGoods })
          }
        >
          {plan.paid === 0 ? "Continue without spending" : `Spend ${plan.paid} influence`}
        </ConfirmButton>
      }
    >
      <Hint>
        You gain <b>3 command tokens</b>. You may also spend any amount of influence to gain{" "}
        <b>1 more for every {plan.perToken}</b> influence spent (extra influence is wasted).
      </Hint>
      <PaymentPicker
        values={plan.values}
        tradeGoodsAvailable={num(o.trade_goods)}
        value={plan.payment}
        onChange={plan.setPayment}
        unit="influence"
        busy={busy}
      />
      <Hint>
        Spending <b>{plan.paid}</b> influence buys <b>{plan.bought}</b> token(s) - you will gain{" "}
        <b>{plan.gain}</b> in total
        {plan.gain < 3 + plan.bought ? ` (limited by ${plan.reinforcements} in reinforcements)` : ""}.
      </Hint>
    </PromptShell>
  );
}

function DistributeStep({
  shell,
  owner,
  busy,
  submit,
  total,
}: PrimaryViewProps & { total: number }) {
  const [split, setSplit] = useState<PoolSplit>(EMPTY_SPLIT);
  const placed = split.tactical + split.fleet + split.strategic;
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Primary"
      subtitle="Place your tokens"
      footer={
        <ConfirmButton
          disabled={busy || placed !== total}
          icon={<IconCheck size={16} />}
          onClick={() => submit({ ...split })}
        >
          Confirm
        </ConfirmButton>
      }
    >
      <PoolDistributor total={total} value={split} onChange={setSplit} player={owner} busy={busy} />
    </PromptShell>
  );
}

export function LeadershipSecondary({
  prompt,
  shell,
  responder,
  busy,
  submit,
  back,
}: SecondaryViewProps) {
  const o = prompt.options;
  const plan = useInfluencePlan(o, 0);
  const [split, setSplit] = useState<PoolSplit>(EMPTY_SPLIT);
  const placed = split.tactical + split.fleet + split.strategic;
  // Przy zmianie płatności rozkład bywa zbyt duży - przytnij do nowego limitu.
  const safeSplit = placed > plan.gain ? EMPTY_SPLIT : split;
  const safePlaced = safeSplit.tactical + safeSplit.fleet + safeSplit.strategic;
  return (
    <PromptShell
      hue={shell.hue}
      initiative={shell.initiative}
      title={shell.title}
      badge="Secondary"
      subtitle="Spend influence for command tokens"
      footer={
        <>
          <Button variant="default" disabled={busy} leftSection={<IconArrowLeft size={16} />} onClick={back}>
            Back
          </Button>
          <ConfirmButton
            disabled={busy || safePlaced !== plan.gain}
            icon={<IconCheck size={16} />}
            onClick={() =>
              submit({
                planets: plan.payment.planets,
                trade_goods: plan.payment.tradeGoods,
                ...safeSplit,
              })
            }
          >
            {plan.gain === 0 ? "Follow without tokens" : `Gain ${plan.gain} token(s)`}
          </ConfirmButton>
        </>
      }
    >
      <Hint>
        Spend any amount of influence: <b>1 command token for every {plan.perToken}</b>. This
        costs no token from your strategy pool.
      </Hint>
      <PaymentPicker
        values={plan.values}
        tradeGoodsAvailable={num(o.trade_goods)}
        value={plan.payment}
        onChange={(next) => {
          plan.setPayment(next);
          setSplit(EMPTY_SPLIT);
        }}
        unit="influence"
        busy={busy}
      />
      {plan.gain > 0 ? (
        <PoolDistributor
          total={plan.gain}
          value={safeSplit}
          onChange={setSplit}
          player={responder}
          busy={busy}
        />
      ) : (
        <Hint>
          Spending <b>{plan.paid}</b> influence is not enough for a token yet.
        </Hint>
      )}
    </PromptShell>
  );
}
