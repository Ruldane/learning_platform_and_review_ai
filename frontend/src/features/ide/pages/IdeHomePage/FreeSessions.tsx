import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { FreeSessionView } from "../../components/viewTypes";

interface FreeSessionsProps {
  sessions: FreeSessionView[];
  busy: boolean;
  onStart: () => void;
  onResume: (sessionId: string) => void;
}

/** Les séances sans exercice : en ouvrir une, ou reprendre une des précédentes. */
export function FreeSessions({ sessions, busy, onStart, onResume }: FreeSessionsProps) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <h2 id={headingId} className="text-lg font-medium">
        {t("ide.home.free")}
      </h2>
      <p className="max-w-prose text-sm text-muted-foreground">{t("ide.home.freeIntro")}</p>
      <Button className="self-start" aria-disabled={busy} onClick={busy ? undefined : onStart}>
        {t("ide.home.freeStart")}
      </Button>
      {sessions.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("ide.home.freeEmpty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {sessions.map((session) => (
            <li key={session.id} className="flex flex-wrap items-center gap-3">
              <span>{session.title}</span>
              <Button
                variant="outline"
                size="sm"
                aria-disabled={busy}
                aria-label={t("ide.home.resumeFree", { title: session.title })}
                onClick={() => !busy && onResume(session.id)}
              >
                {t("ide.home.resume")}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
