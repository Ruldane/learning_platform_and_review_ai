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

/** Fournisseur choisi vers un fournisseur à saisie libre, en attente du nom du modèle. */
interface PendingProvider {
  provider: string;
  /** Valeur à laquelle ce choix se rapporte : il tombe si elle change (préréglage, rechargement). */
  base: ModelChoice;
}

/** Liste des modèles proposés, ou `null` pour une saisie libre (aucune liste, ou liste vide). */
function listedModels(providers: ProviderOption[], name: string) {
  const models = providers.find((option) => option.name === name)?.models;
  return models?.length ? models : null;
}

/** Fournisseur puis modèle d'un niveau : liste déroulante, ou saisie libre sans liste. */
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
      // Saisie libre : rien n'est enregistré tant que le modèle n'est pas saisi.
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
