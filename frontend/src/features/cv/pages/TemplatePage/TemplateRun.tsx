import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "../../hooks/useRun";
import { RunFeed } from "../RunFeed";
import { TEMPLATE_QUESTION, TemplateQuestion } from "./TemplateQuestion";

interface TemplateRunProps {
  sessionId: string;
  /** Appelé à chaque changement d'état ou nouvelle question : la page relit le modèle. */
  onChange: () => void;
  createSocket?: SocketFactory;
}

/** Le fil du Maquettiste ; la question `cv_template` a sa carte, les autres la carte commune. */
export function TemplateRun({ sessionId, onChange, createSocket }: TemplateRunProps) {
  const run = useRun(sessionId, onChange, createSocket);
  return (
    <RunFeed
      run={run}
      label={t("cv.templatePage.feed")}
      renderInterrupt={(item) =>
        item.interrupt.kind === TEMPLATE_QUESTION ? (
          <TemplateQuestion item={item} run={run} />
        ) : undefined
      }
    />
  );
}
