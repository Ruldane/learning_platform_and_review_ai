import { useQueryClient } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { cvKeys } from "../../queryKeys";

interface ProfileRunProps {
  sessionId: string;
  createSocket?: SocketFactory;
}

/**
 * Live reading of the documents. At the end of the session, the profile is reloaded: the draft
 * appears in place of the thread. A stopped session says so and offers to restart the import.
 */
export function ProfileRun({ sessionId, createSocket }: ProfileRunProps) {
  const client = useQueryClient();
  const reload = () => void client.invalidateQueries({ queryKey: cvKeys.profile });
  const run = useRun(sessionId, reload, createSocket);
  const stopped = run.stream.status === "failed" || run.stream.status === "cancelled";
  return (
    <section className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">{t("cv.profilePage.capturing")}</p>
      <RunFeed run={run} label={t("cv.profilePage.captureFeed")} />
      {stopped ? (
        <div className="flex flex-col items-start gap-2">
          <InlineError
            message={run.stream.view.error?.message ?? t("cv.profilePage.captureFailed")}
          />
          <Button variant="outline" onClick={reload}>
            {t("cv.profilePage.captureRetry")}
          </Button>
        </div>
      ) : null}
    </section>
  );
}
