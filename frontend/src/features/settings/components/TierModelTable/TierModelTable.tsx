import { t } from "@/shared/i18n/t";
import { TierModelSelect } from "../TierModelSelect";
import { TIERS } from "../viewTypes";
import type { ModelChoice, ProviderOption, Tier, TierChoices } from "../viewTypes";

interface TierModelTableProps {
  tiers: TierChoices;
  providers: ProviderOption[];
  onChange: (tier: Tier, choice: ModelChoice) => void;
  disabled?: boolean;
}

/** Les quatre niveaux, leur usage (spec 11.2) et le modèle choisi pour chacun. */
export function TierModelTable({
  tiers,
  providers,
  onChange,
  disabled = false,
}: TierModelTableProps) {
  return (
    <table className="w-full border-collapse text-left text-sm">
      <caption className="sr-only">{t("settings.tiers.title")}</caption>
      <thead>
        <tr className="border-b border-border text-muted-foreground">
          <th scope="col" className="py-2 pr-4 font-medium">
            {t("settings.tiers.columns.tier")}
          </th>
          <th scope="col" className="py-2 pr-4 font-medium">
            {t("settings.tiers.columns.usage")}
          </th>
          <th scope="col" className="py-2 font-medium">
            {t("settings.tiers.columns.model")}
          </th>
        </tr>
      </thead>
      <tbody>
        {TIERS.map((tier) => (
          <tr key={tier} className="border-b border-border align-top">
            <th scope="row" className="py-3 pr-4 font-medium">
              {t(`settings.tiers.${tier}.label`)}
            </th>
            <td className="py-3 pr-4 text-muted-foreground">{t(`settings.tiers.${tier}.usage`)}</td>
            <td className="py-3">
              <TierModelSelect
                tier={tier}
                value={tiers[tier]}
                providers={providers}
                disabled={disabled}
                onChange={(choice) => onChange(tier, choice)}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
