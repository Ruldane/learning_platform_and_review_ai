import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import type { CommitteeStatusView } from "../../types";

interface ResultGateProps {
  status: CommitteeStatusView;
  children: ReactNode;
}

/** The result once the committee has finished; before that, or if it stopped, the sentence saying
 * where it is. */
export function ResultGate({ status, children }: ResultGateProps) {
  if (status === "done") return <>{children}</>;
  return (
    <p className="max-w-prose text-muted-foreground">
      {t(`applications.committeeWaiting.${status}`)}
    </p>
  );
}
