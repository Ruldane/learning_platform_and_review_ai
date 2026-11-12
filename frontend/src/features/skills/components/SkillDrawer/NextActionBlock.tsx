import { t } from "@/shared/i18n/t";
import type { NextActionView } from "../viewTypes";
import { SmartLink } from "./SmartLink";

/** La prochaine action pour monter d'un niveau ; sans lien quand elle n'est pas encore possible. */
export function NextActionBlock({ action }: { action: NextActionView | null }) {
  if (action === null) {
    return <p className="text-sm text-muted-foreground">{t("skills.drawer.nextActionNone")}</p>;
  }
  return (
    <p className="text-sm">
      {action.url ? <SmartLink url={action.url}>{action.label}</SmartLink> : action.label}
    </p>
  );
}
