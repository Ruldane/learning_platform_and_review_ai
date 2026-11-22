import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { analyzedOffers, editDraft, latestDraft, prepareDraft, type ProfileText } from "../../api";
import { DraftEditor } from "./DraftEditor";
import { StartDraft } from "./StartDraft";

const DRAFT = ["linkedin-drafts", "latest"];

export function LinkedInPage() {
  const cache = useQueryClient();
  const heading = useRef<HTMLHeadingElement>(null);
  const query = useQuery({
    queryKey: DRAFT, queryFn: ({ signal }) => latestDraft(signal),
    refetchInterval: ({ state }) => state.data?.state === "pending" ? 900 : false,
  });
  const offers = useQuery({ queryKey: ["linkedin-offers"], queryFn: ({ signal }) => analyzedOffers(signal) });
  const prepare = useMutation({
    mutationFn: prepareDraft,
    onSuccess: (draft) => { cache.setQueryData(DRAFT, draft); },
  });
  const edit = useMutation({
    mutationFn: ({ id, revision, text }: { id: string; revision: number; text: ProfileText }) =>
      editDraft(id, revision, text),
    onSuccess: (draft) => {
      cache.setQueryData(DRAFT, draft);
      requestAnimationFrame(() => heading.current?.focus());
    },
  });
  const draft = query.data;
  const error = prepare.error || edit.error || query.error;
  return (
    <section className="grid max-w-3xl gap-5">
      <h1 className="text-2xl font-semibold" tabIndex={-1} ref={heading}>
        {t("linkedInDrafts.title")}
      </h1>
      <StartDraft offers={offers.data ?? []} busy={prepare.isPending || draft?.state === "pending"}
        onStart={prepare.mutate} />
      {error ? <InlineError message={errorMessage(error)} /> : null}
      {draft && draft.state !== "ready" ? <p role="status">{t(`linkedInDrafts.${draft.state}`)}</p> : null}
      {draft?.text && draft.state === "ready" ? (
        <DraftEditor key={draft.id + ":" + draft.revision} draft={draft} text={draft.text}
          busy={edit.isPending} onSave={(text) => edit.mutate({ id: draft.id, revision: draft.revision, text })} />
      ) : null}
    </section>
  );
}
