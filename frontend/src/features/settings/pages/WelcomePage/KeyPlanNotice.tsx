import { t } from "@/shared/i18n/t";
import type { KeyPlan } from "../../keyPlan";

/** What the step will do to the models: they move to the key's provider, or they must be set. */
export function KeyPlanNotice({ plan }: { plan: KeyPlan }) {
  if (plan.moveTo) {
    return <p className="text-sm">{t("onboarding.key.moveTo", { provider: plan.moveTo })}</p>;
  }
  if (plan.unmatched) {
    return <p className="text-sm">{t("onboarding.key.noPreset", { provider: plan.unmatched })}</p>;
  }
  return null;
}
