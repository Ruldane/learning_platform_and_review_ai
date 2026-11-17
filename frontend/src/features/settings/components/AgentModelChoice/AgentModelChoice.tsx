import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { ModelField } from "../ModelField";
import { ProviderSelect } from "../ProviderSelect";
import type { ModelChoice, ProviderOption } from "../viewTypes";

interface AgentModelChoiceProps {
  /** Nom de l'agent, pour les étiquettes lues par les lecteurs d'écran. */
  agentName: string;
  /** Texte du choix « aucun » : « Niveau par défaut (Standard) ». */
  defaultLabel: string;
  /** Le modèle choisi pour cet agent, ou rien : il suit son niveau. */
  value: ModelChoice | undefined;
  providers: ProviderOption[];
  disabled?: boolean;
  /** `null` : on revient au niveau par défaut. */
  onChange: (choice: ModelChoice | null) => void;
}

/** Fournisseur choisi vers un fournisseur à saisie libre, en attente du nom du modèle. */
interface PendingProvider {
  provider: string;
  /** Valeur à laquelle ce choix se rapporte : il tombe si elle change (rechargement, retrait). */
  base: ModelChoice | undefined;
}

const sameChoice = (a: ModelChoice | undefined, b: ModelChoice | undefined) =>
  a?.provider === b?.provider && a?.model === b?.model;

/** Liste des modèles proposés, ou `null` pour une saisie libre (aucune liste, ou liste vide). */
function listedModels(providers: ProviderOption[], name: string) {
  const models = providers.find((option) => option.name === name)?.models;
  return models?.length ? models : null;
}

/** Les deux gestes de la ligne : choisir un fournisseur (ou « aucun »), valider un modèle. */
function useChoiceActions(args: {
  providers: ProviderOption[];
  value: ModelChoice | undefined;
  provider: string;
  onChange: (choice: ModelChoice | null) => void;
  setPending: (pending: PendingProvider | null) => void;
}) {
  const { providers, value, provider, onChange, setPending } = args;
  function pickProvider(name: string) {
    setPending(null);
    if (name === "") {
      if (value) onChange(null);
      return;
    }
    const first = listedModels(providers, name)?.[0];
    if (first === undefined) {
      setPending({ provider: name, base: value }); // saisie libre : le modèle suit
      return;
    }
    onChange({ provider: name, model: first });
  }

  function commitModel(text: string) {
    const model = text.trim();
    if (!model || sameChoice({ provider, model }, value)) return;
    setPending(null);
    onChange({ provider, model });
  }
  return { pickProvider, commitModel };
}

/**
 * Le modèle d'un agent : « niveau par défaut », ou un fournisseur puis un modèle (liste, ou saisie
 * libre sans liste). Rien n'est envoyé tant qu'un fournisseur à saisie libre n'a pas son modèle.
 */
export function AgentModelChoice({
  agentName,
  defaultLabel,
  value,
  providers,
  onChange,
  disabled = false,
}: AgentModelChoiceProps) {
  const [pending, setPending] = useState<PendingProvider | null>(null);
  const waiting = pending && sameChoice(pending.base, value) ? pending.provider : null;
  const provider = waiting ?? value?.provider ?? "";
  const models = provider ? listedModels(providers, provider) : null;
  const { pickProvider, commitModel } = useChoiceActions({
    providers,
    value,
    provider,
    onChange,
    setPending,
  });

  return (
    <div className="flex flex-wrap gap-2">
      <ProviderSelect
        label={t("settings.agents.providerLabel", { agent: agentName })}
        value={provider}
        options={providers}
        emptyLabel={defaultLabel}
        disabled={disabled}
        onPick={pickProvider}
      />
      {provider ? (
        <ModelField
          label={t("settings.agents.modelLabel", { agent: agentName })}
          models={models}
          value={waiting ? "" : (value?.model ?? "")}
          disabled={disabled}
          onCommit={commitModel}
        />
      ) : null}
    </div>
  );
}
