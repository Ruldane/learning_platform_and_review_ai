import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { TEMPLATE_QUESTION, TemplateQuestion } from "./TemplateQuestion";

interface TemplateRunProps {
  sessionId: string;
  /** Called on each state change or new question: the page reloads the template. */
  onChange: () => void;
  /** The template is ready: the validation question no longer applies. */
  ready?: boolean;
  createSocket?: SocketFactory;
}

/**
 * The Maquettiste's thread; the `cv_template` question has its own card, the others share one. Once
 * the template is ready or the session is over, the validation card is hidden (fields and buttons
 * greyed out under « Terminée » tell nothing).
 */
export function TemplateRun({
  sessionId,
  onChange,
  ready = false,
  createSocket,
}: TemplateRunProps) {
  const run = useRun(sessionId, onChange, createSocket);
  return (
    <RunFeed
      run={run}
      label={t("cv.templatePage.feed")}
      renderInterrupt={(item) =>
        item.interrupt.kind !== TEMPLATE_QUESTION ? undefined : ready || run.over ? null : (
          <TemplateQuestion item={item} run={run} />
        )
      }
    />
  );
}
