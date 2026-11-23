import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { PRESET_NAMES, TIERS, type PresetMap, type PresetName, type ProviderModels, type TierChoices } from "../../types";

export function MissingProviderWarning({ providers, current, presets, busy, onApply }: {
  providers: ProviderModels[];
  current: TierChoices;
  presets: PresetMap;
  busy: boolean;
  onApply: (name: PresetName) => void;
}) {
  const available = new Set(providers.filter((provider) => provider.has_key).map(({ name }) => name));
  const selected = [...new Set(TIERS.map((tier) => current[tier].provider).filter(Boolean))];
  const missing = selected.filter((provider) => !available.has(provider));
  if (!missing.length) return null;
  const names = missing.map((name) => providers.find((provider) => provider.name === name)?.label ?? name);
  const alternative = PRESET_NAMES.find((name) =>
    TIERS.every((tier) => available.has(presets[name][tier].provider)),
  );
  return (
    <section className="grid gap-3 rounded-lg border bg-muted p-4" aria-label={t("settings.models.readiness.title")}>
      <p className="text-sm" role="status">
        {t("settings.models.readiness.missing", { providers: names.join(", ") })}
      </p>
      {alternative ? (
        <Button type="button" variant="outline" className="justify-self-start" disabled={busy}
          onClick={() => onApply(alternative)}>
          {t("settings.models.readiness.apply", { preset: t(`settings.presets.${alternative}`) })}
        </Button>
      ) : (
        <p className="text-sm">{t("settings.models.readiness.addKey")}</p>
      )}
    </section>
  );
}
