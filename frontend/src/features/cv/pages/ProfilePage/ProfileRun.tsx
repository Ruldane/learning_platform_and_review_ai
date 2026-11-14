import { useQueryClient } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useRun } from "../../hooks/useRun";
import { cvKeys } from "../../queryKeys";
import { RunFeed } from "../RunFeed";

interface ProfileRunProps {
  sessionId: string;
  createSocket?: SocketFactory;
}

/**
 * La lecture des documents en direct. À la fin de la session, le profil est relu : le brouillon
 * apparaît à la place du fil. Une session arrêtée le dit et propose de recommencer l'import.
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
