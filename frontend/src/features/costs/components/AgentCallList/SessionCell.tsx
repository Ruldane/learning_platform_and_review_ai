import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { CallView } from "../viewTypes";

const SESSION_REF = 8;

/** La session d'un appel : sa référence courte (l'identifiant en infobulle) et l'écran du parcours. */
export function SessionCell({ call }: { call: CallView }) {
  if (!call.sessionId) return <span aria-hidden="true">–</span>;
  return (
    <span className="flex flex-wrap items-baseline gap-x-2">
      <code title={call.sessionId} className="text-xs">
        {call.sessionId.slice(0, SESSION_REF)}
      </code>
      {call.screenPath ? (
        <Link
          to={call.screenPath}
          aria-label={t("costs.log.openLabel", { graph: call.graphLabel })}
          className="underline"
        >
          {t("costs.log.open")}
        </Link>
      ) : null}
    </span>
  );
}
