import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { TokenForm } from "../../components/TokenForm";
import { TokenRevealOnce } from "../../components/TokenRevealOnce";
import type { TokenDraft } from "../../components/viewTypes";
import { useCreateToken } from "../../hooks/useCreateToken";
import { useMcpFeatures } from "../../hooks/useMcpFeatures";

/**
 * Le formulaire de création et, juste après, le jeton montré une seule fois. La valeur reste dans
 * la mutation, en mémoire : « J'ai copié le jeton » l'oublie, un rechargement aussi. Le formulaire
 * repart vide après chaque création (nouvelle `key`).
 */
export function TokenCreator({ onClosed }: { onClosed: () => void }) {
  const { query, options } = useMcpFeatures();
  const create = useCreateToken();
  const [formKey, setFormKey] = useState(0);
  async function submit(draft: TokenDraft) {
    try {
      await create.mutateAsync({
        label: draft.label,
        features: draft.features,
        mode: draft.mode,
        expires_in_days: draft.expiresInDays,
      });
      setFormKey((key) => key + 1);
    } catch {
      // L'erreur est affichée sous le formulaire (`create.error`), la saisie reste.
    }
  }
  function done() {
    create.reset();
    onClosed();
  }
  return (
    <div className="flex flex-col gap-3">
      {create.data ? (
        <TokenRevealOnce
          token={{ token: create.data.token, label: create.data.label }}
          onDone={done}
        />
      ) : null}
      {query.isPending ? <LoadingState /> : null}
      {query.isError ? <InlineError message={errorMessage(query.error)} /> : null}
      {query.data ? (
        <TokenForm key={formKey} features={options} pending={create.isPending} onSubmit={submit} />
      ) : null}
      {create.isError ? <InlineError message={errorMessage(create.error)} /> : null}
    </div>
  );
}
