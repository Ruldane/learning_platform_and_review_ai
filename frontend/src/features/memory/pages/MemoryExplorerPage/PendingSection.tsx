import { errorMessage } from "@/shared/api/errors";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { PendingDecisions } from "../../components/PendingDecisions";
import { PENDING_FILTERS } from "../../filters";
import { useItemMutations } from "../../hooks/useItemMutations";
import { useMemoryItems } from "../../hooks/useMemoryItems";

const QUERY = { filters: PENDING_FILTERS, status: "pending", offset: 0, limit: 50 } as const;

/** « À confirmer » : les décisions proposées par les agents ; la boîte disparaît quand elle est vide. */
export function PendingSection() {
  const pending = useMemoryItems(QUERY);
  const { confirm, reject } = useItemMutations();

  if (pending.isError) {
    return (
      <ErrorState message={errorMessage(pending.error)} onRetry={() => void pending.refetch()} />
    );
  }
  if (!pending.data || pending.data.items.length === 0) return null;

  const busyId = confirm.isPending ? confirm.variables : reject.isPending ? reject.variables : null;
  const failure = confirm.error ?? reject.error;
  return (
    <div className="flex flex-col gap-2">
      <PendingDecisions
        items={pending.data.items}
        busyId={busyId ?? null}
        onConfirm={(id) => confirm.mutate(id)}
        onReject={(id) => reject.mutate(id)}
      />
      {failure ? <InlineError message={errorMessage(failure)} /> : null}
    </div>
  );
}
