import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { detailKey, listKey, reviewCommitment } from "../../api";
import { normalizeMeasure } from "../../format";

export function ObservationForm({ id, saved }: { id: string; saved: () => void }) {
  const [observed, setObserved] = useState("");
  const [note, setNote] = useState("");
  const cache = useQueryClient();
  const review = useMutation({
    mutationFn: () => reviewCommitment(id, { observed: normalizeMeasure(observed), note }),
    onSuccess: (item) => {
      saved();
      cache.setQueryData(detailKey(id), item);
      return cache.invalidateQueries({ queryKey: listKey, exact: true });
    },
  });
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (observed.trim() && !review.isPending) review.mutate();
      }}
    >
      <label className="flex flex-col gap-1">
        {t("datedCommitments.measure")}
        <input
          required
          inputMode="decimal"
          maxLength={32}
          value={observed}
          onChange={(event) => setObserved(event.target.value)}
          className="rounded border border-border bg-background p-2"
        />
      </label>
      <label className="flex flex-col gap-1">
        {t("datedCommitments.note")}
        <textarea
          rows={3}
          maxLength={1500}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          className="rounded border border-border bg-background p-2"
        />
      </label>
      {review.isError && <p role="alert">{errorMessage(review.error)}</p>}
      <Button type="submit" className="self-start" aria-disabled={review.isPending}>
        {t("datedCommitments.review")}
      </Button>
    </form>
  );
}
