import { useState } from "react";
import { IconCheck, IconCrown, IconLock } from "@tabler/icons-react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { AppModal } from "@/shared/ui/AppModal";
import {
  ConfirmButton,
  Hint,
  PaymentPicker,
  paymentTotal,
  type Payment,
} from "@/domains/strategy/PromptParts";
import type { CustodiansView } from "./useInvasion";
import styles from "./CustodiansClaim.module.css";

/**
 * Żeton Custodians na Mecatol Rex (R_custodians_token): dopóki leży, nie wolno tam lądować.
 * Przed krokiem Commit Ground Forces aktywny gracz może go zdjąć za 6 wpływu (+1 VP, faza
 * agendy w każdej następnej rundzie) i wtedy MUSI zlądować na Mecatol Rex. Legalność sprawdza
 * silnik - baner tylko zbiera płatność (planety + trade goods).
 */
export function CustodiansClaim({
  view,
  busy,
  onClaim,
}: {
  view: CustodiansView;
  busy: boolean;
  onClaim: (planets: string[], tradeGoods: number) => Promise<void>;
}) {
  const [opened, setOpened] = useState(false);
  const [payment, setPayment] = useState<Payment>({ planets: [], tradeGoods: 0 });
  const [working, setWorking] = useState(false);

  if (view.claimed) {
    return (
      <div className={styles.banner} data-done role="status">
        <img
          className={styles.token}
          src={assetUrl("/tokens/token_custodianvp.png")}
          alt=""
          aria-hidden="true"
        />
        <span className={styles.text}>
          <b>Custodians token taken (+1 VP)</b>
          <small>Land at least one ground force on Mecatol Rex.</small>
        </span>
      </div>
    );
  }
  if (!view.onBoard) return null;

  const total = paymentTotal(view.influence, payment, view.tradeGoodValue ?? 1);
  const enough = total >= view.cost;

  const submit = async () => {
    if (working) return;
    setWorking(true);
    try {
      await onClaim(payment.planets, payment.tradeGoods);
      setOpened(false);
      setPayment({ planets: [], tradeGoods: 0 });
    } catch {
      // Powód (422) pokazuje panel komunikatów.
    } finally {
      setWorking(false);
    }
  };

  return (
    <>
      <div className={styles.banner}>
        <img
          className={styles.token}
          src={assetUrl("/tokens/token_custodian.png")}
          alt=""
          aria-hidden="true"
        />
        <span className={styles.text}>
          <b>
            <IconLock size={13} aria-hidden="true" /> Mecatol Rex is sealed by the Custodians
            token
          </b>
          <small>
            {view.canClaim
              ? `Remove it for ${view.cost} influence to land here (+1 VP, agenda phase every round).`
              : (view.reason ?? "The token cannot be removed now.")}
          </small>
        </span>
        <button
          type="button"
          className={styles.btn}
          disabled={busy || !view.canClaim}
          title={view.canClaim ? undefined : (view.reason ?? undefined)}
          onClick={() => setOpened(true)}
        >
          <IconCrown size={14} aria-hidden="true" /> Remove token
        </button>
      </div>

      <AppModal
      floating
        opened={opened}
        onClose={() => setOpened(false)}
        title="Custodians token"
        minimizable
        size="lg"
      >
        <div className={styles.modalBody}>
          <div className={styles.modalHead}>
            <img
              className={styles.token}
              src={assetUrl("/tokens/token_custodian.png")}
              alt="Custodians token"
            />
            <Hint>
              Spend <b>{view.cost} influence</b> to take the token from Mecatol Rex. You gain{" "}
              <b>1 victory point</b>, the agenda phase is added to every round from now on, and
              you <b>must land at least one ground force</b> on Mecatol Rex.
            </Hint>
          </div>
          <PaymentPicker
            values={view.influence}
            tradeGoodsAvailable={view.tradeGoods}
            tradeGoodValue={view.tradeGoodValue ?? 1}
            value={payment}
            onChange={setPayment}
            unit="influence"
            busy={working}
            target={view.cost}
          />
          <Hint>
            Selected: <b>{total}</b> of <b>{view.cost}</b> (overpaying is allowed, the surplus is
            lost).
          </Hint>
          <div className={styles.modalFooter}>
            <ConfirmButton
              disabled={working || !enough}
              icon={<IconCheck size={16} />}
              onClick={() => void submit()}
            >
              Take the token
            </ConfirmButton>
          </div>
        </div>
      </AppModal>
    </>
  );
}
