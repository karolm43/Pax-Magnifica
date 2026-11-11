import { useState } from "react";
import { IconBug } from "@tabler/icons-react";
import { Button } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { throwResponseError } from "@/api/fetchJson";
import hud from "@/shared/ui/hudChrome.module.css";
import { captureScreenshot } from "./captureScreenshot";
import { recentConsoleErrors } from "./consoleCapture";
import classes from "./BugReport.module.css";

/*
 * „Report bug": zrzut ekranu ROBIONY NAJPIERW (zanim otworzy się okno, żeby było widać grę,
 * nie formularz), potem okno z podglądem i polem opisu. Wysyłka trafia na backend hosta
 * (`POST /bug-report`) — także od gościa w grze sieciowej, bo żądanie niesie jego token miejsca
 * (opakowanie `fetch` z `installActorIdentity`). Raport ląduje w `bug_reports/` na dysku hosta.
 */
const ENDPOINT = "/bot/bug-report";

type Status =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "sent"; reportId: string }
  | { kind: "error"; message: string };

export function BugReportButton() {
  const [capturing, setCapturing] = useState(false);
  const [opened, setOpened] = useState(false);
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [includeShot, setIncludeShot] = useState(true);
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const open = async () => {
    if (capturing) return;
    setCapturing(true);
    const shot = await captureScreenshot();
    setCapturing(false);
    setScreenshot(shot);
    setIncludeShot(shot !== null);
    setDescription("");
    setStatus({ kind: "idle" });
    setOpened(true);
  };

  const send = async () => {
    setStatus({ kind: "sending" });
    try {
      const response = await fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description,
          screenshot: includeShot ? screenshot : null,
          client: {
            url: window.location.href,
            userAgent: navigator.userAgent,
            viewport: {
              width: window.innerWidth,
              height: window.innerHeight,
              dpr: window.devicePixelRatio,
            },
            consoleErrors: recentConsoleErrors(),
          },
        }),
      });
      if (!response.ok) await throwResponseError(response, "Could not send the report.");
      const body = (await response.json()) as { report_id: string };
      setStatus({ kind: "sent", reportId: body.report_id });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "Could not send the report.",
      });
    }
  };

  const canSend =
    status.kind !== "sending" &&
    status.kind !== "sent" &&
    (description.trim().length > 0 || (includeShot && screenshot !== null));

  return (
    <>
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconBug size={14} />}
        disabled={capturing}
        onClick={() => void open()}
        title="Report a bug (takes a screenshot of your view)"
        aria-label="Report bug"
        data-bug-report-ignore=""
      >
        <span className={hud.hudLabel}>{capturing ? "Capturing…" : "Bug"}</span>
      </Button>
      <AppModal
        opened={opened}
        onClose={() => setOpened(false)}
        title="Report a bug"
        size={640}
      >
        <div className={classes.body} data-bug-report-ignore="">
          {screenshot ? (
            <label className={classes.shotRow}>
              <input
                type="checkbox"
                checked={includeShot}
                onChange={(e) => setIncludeShot(e.currentTarget.checked)}
              />
              <span>Attach this screenshot</span>
            </label>
          ) : (
            <p className={classes.note}>
              The screenshot could not be captured — the description and the game state will
              still be sent.
            </p>
          )}
          {screenshot && (
            <img
              className={classes.preview}
              src={screenshot}
              alt="Screenshot of your view"
              data-dimmed={!includeShot || undefined}
            />
          )}
          <textarea
            className={classes.textarea}
            aria-label="What went wrong?"
            placeholder="What happened? What did you expect? What did you click just before?"
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            disabled={status.kind === "sent"}
            autoFocus
          />
          <p className={classes.note}>
            The report (with the current game state) is saved on the host&apos;s computer.
          </p>
          {status.kind === "error" && <p className={classes.error}>{status.message}</p>}
          {status.kind === "sent" && (
            <p className={classes.sent} role="status">
              Report sent — thank you! ({status.reportId})
            </p>
          )}
          <div className={classes.actions}>
            <Button variant="default" size="sm" onClick={() => setOpened(false)}>
              {status.kind === "sent" ? "Close" : "Cancel"}
            </Button>
            {status.kind !== "sent" && (
              <Button
                size="sm"
                onClick={() => void send()}
                disabled={!canSend}
                loading={status.kind === "sending"}
              >
                Send report
              </Button>
            )}
          </div>
        </div>
      </AppModal>
    </>
  );
}
