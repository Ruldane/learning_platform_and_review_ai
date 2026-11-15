import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import type { CommitteeStatusView } from "../../types";

interface ResultGateProps {
  status: CommitteeStatusView;
  children: ReactNode;
}

/** Le résultat une fois le comité terminé ; avant, ou s'il s'est arrêté, la phrase qui dit où il en est. */
export function ResultGate({ status, children }: ResultGateProps) {
  if (status === "done") return <>{children}</>;
  return (
    <p className="max-w-prose text-muted-foreground">
      {t(`applications.committeeWaiting.${status}`)}
    </p>
  );
}
