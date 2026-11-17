import { t } from "@/shared/i18n/t";
import type { KeyPlan } from "../../keyPlan";

/** Ce que l'étape fera des modèles : ils passent sur le fournisseur de la clé, ou il faut les régler. */
export function KeyPlanNotice({ plan }: { plan: KeyPlan }) {
  if (plan.moveTo) {
    return <p className="text-sm">{t("onboarding.key.moveTo", { provider: plan.moveTo })}</p>;
  }
  if (plan.unmatched) {
    return <p className="text-sm">{t("onboarding.key.noPreset", { provider: plan.unmatched })}</p>;
  }
  return null;
}
