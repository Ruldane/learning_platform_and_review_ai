import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { ModelField } from "../ModelField";
import { ProviderSelect } from "../ProviderSelect";
import type { ModelChoice, ProviderOption, Tier } from "../viewTypes";

interface TierModelSelectProps {
  tier: Tier;
  value: ModelChoice;
  providers: ProviderOption[];
  onChange: (value: ModelChoice) => void;
  disabled?: boolean;
}

/** Provider chosen for free-text entry, waiting for the model name. */
interface PendingProvider {
  provider: string;
  /** Value this choice refers to: it drops if that value changes (preset, reload). */
  base: ModelChoice;
}

/** List of offered models, or `null` for free-text entry (no list, or an empty list). */
function listedModels(providers: ProviderOption[], name: string) {
  const models = providers.find((option) => option.name === name)?.models;
  return models?.length ? models : null;
}

/** Provider then model of a level: a dropdown, or free-text entry without a list. */
export function TierModelSelect({
  tier,
  value,
  providers,
  onChange,
  disabled = false,
}: TierModelSelectProps) {
  const [pending, setPending] = useState<PendingProvider | null>(null);
  const waiting =
    pending?.base.provider === value.provider && pending.base.model === value.model
      ? pending.provider
      : null;
  const provider = waiting ?? value.provider;
  const models = listedModels(providers, provider);
  const tierLabel = t(`settings.tiers.${tier}.label`);

  function pickProvider(name: string) {
    const first = listedModels(providers, name)?.[0];
    if (first === undefined) {
      // Free text: nothing is saved until the model is entered.
      setPending({ provider: name, base: value });
      return;
    }
    setPending(null);
    onChange({ provider: name, model: first });
  }

  function commitModel(text: string) {
    const model = text.trim();
    if (!model || (model === value.model && provider === value.provider)) return;
    setPending(null);
    onChange({ provider, model });
  }

  return (
    <div className="flex flex-wrap gap-2">
      <ProviderSelect
        label={t("settings.tiers.providerLabel", { tier: tierLabel })}
        value={provider}
        options={providers}
        disabled={disabled}
        onPick={pickProvider}
      />
      <ModelField
        label={t("settings.tiers.modelLabel", { tier: tierLabel })}
        models={models}
        value={waiting ? "" : value.model}
        disabled={disabled}
        onCommit={commitModel}
      />
    </div>
  );
}
