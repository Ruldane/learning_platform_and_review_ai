import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { Rules, WeightKey } from "../../../api";

const CRITERIA: WeightKey[] = ["match", "work_mode", "location"];
const MODES = ["remote", "hybrid", "onsite"] as const;

interface RuleProps {
  rules: Rules;
  onChange: (rules: Rules) => void;
}

export function RuleFields({ rules, onChange }: RuleProps) {
  const weights = rules.weights ?? { match: 50, work_mode: 50, location: 50 };
  return (
    <fieldset className="grid gap-3">
      <legend className="font-medium">{t("offerComparison.weights")}</legend>
      <p className="text-sm">{t("offerComparison.scale")}</p>
      <div className="grid gap-3 sm:grid-cols-3">
        {CRITERIA.map((key) => (
          <label className="grid gap-1" key={key}>
            {t(`offerComparison.criterion.${key}`)}
            <input type="number" min={0} max={100} step={1} className={fieldClass} value={weights[key]}
              onChange={(event) => {
                const value = Number(event.target.value);
                if (Number.isInteger(value) && value >= 0 && value <= 100) {
                  onChange({ ...rules, weights: { ...weights, [key]: value } });
                }
              }} />
          </label>
        ))}
      </div>
      <label className="grid gap-1">
        {t("offerComparison.preferredMode")}
        <select className={fieldClass} value={rules.preferred_work_mode ?? ""} onChange={(event) => {
          const mode = MODES.find((item) => item === event.target.value);
          onChange({ ...rules, preferred_work_mode: mode ?? null });
        }}>
          <option value="">{t("offerComparison.unspecified")}</option>
          {MODES.map((item) => <option key={item} value={item}>{t(`offerComparison.modes.${item}`)}</option>)}
        </select>
      </label>
      <label className="grid gap-1">
        {t("offerComparison.preferredLocation")}
        <input className={fieldClass} value={rules.preferred_location ?? ""} maxLength={120}
          onChange={(event) => onChange({ ...rules, preferred_location: event.target.value || null })} />
      </label>
    </fieldset>
  );
}
