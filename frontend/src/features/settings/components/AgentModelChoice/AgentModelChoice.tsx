import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { ModelField } from "../ModelField";
import { ProviderSelect } from "../ProviderSelect";
import type { ModelChoice, ProviderOption } from "../viewTypes";

interface AgentModelChoiceProps {
  /** Agent name, for the labels read by screen readers. */
  agentName: string;
  /** Text of the « aucun » choice: « Niveau par défaut (Standard) ». */
  defaultLabel: string;
  /** The model chosen for this agent, or nothing: it follows its level. */
  value: ModelChoice | undefined;
  providers: ProviderOption[];
  disabled?: boolean;
  /** `null`: back to the default level. */
  onChange: (choice: ModelChoice | null) => void;
}

/** Provider chosen for free-text entry, waiting for the model name. */
interface PendingProvider {
  provider: string;
  /** Value this choice refers to: it drops if that value changes (reload, removal). */
  base: ModelChoice | undefined;
}

const sameChoice = (a: ModelChoice | undefined, b: ModelChoice | undefined) =>
  a?.provider === b?.provider && a?.model === b?.model;

/** Models offered, or `null` for free-text entry (no list, or an empty list). */
function listedModels(providers: ProviderOption[], name: string) {
  const models = providers.find((option) => option.name === name)?.models;
  return models?.length ? models : null;
}

/** The two gestures of the row: pick a provider (or « aucun »), confirm a model. */
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
      setPending({ provider: name, base: value }); // free-text entry: the model follows
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
 * The model of an agent: « niveau par défaut », or a provider then a model (list, or free
 * text without a list). Nothing is sent while a free-text provider has no model yet.
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
  const hintId = useId();
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
          describedBy={waiting ? hintId : undefined}
          onCommit={commitModel}
        />
      ) : null}
      {waiting ? (
        <p id={hintId} className="w-full text-sm text-muted-foreground">
          {t("settings.agents.modelHint")}
        </p>
      ) : null}
    </div>
  );
}
