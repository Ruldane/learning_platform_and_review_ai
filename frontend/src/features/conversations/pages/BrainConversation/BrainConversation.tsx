import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ConversationList } from "../../components/ConversationList";
import { useConversationList } from "../../hooks/useConversationList";
import { createBrainThread } from "../../threadsApi";
import { BrainThread } from "./BrainThread";
import { useBrainSelection } from "./useBrainSelection";

export function BrainConversation() {
  const { requested, select } = useBrainSelection();
  const [revision, clear] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const { sidebar, refresh, listPending } = useConversationList("brain", (action) => {
    if (action.kind === "clear") {
      clear((current) => current + 1);
      heading.current?.focus();
    }
    if (action.kind === "delete" || action.kind === "wipe") select(null);
  });
  const create = useMutation({
    mutationFn: createBrainThread,
    onSuccess: (thread) => {
      refresh();
      select(thread.id);
      heading.current?.focus();
    },
  });
  const id = requested ?? sidebar.entries[0]?.id ?? null;
  return (
    <section className="flex flex-col gap-3" aria-labelledby="brain-thread-heading">
      <h2 ref={heading} id="brain-thread-heading" tabIndex={-1} className="text-lg font-semibold">
        {t("brain.chat.title")}
      </h2>
      <div className="grid items-start gap-4 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <ConversationList
          {...sidebar}
          heading="h3"
          selected={id}
          busy={sidebar.busy || create.isPending}
          error={create.error ? errorMessage(create.error) : sidebar.error}
          onCreate={() => create.mutate()}
          onSelect={select}
        />
        {listPending ? null : (
          <BrainThread key={`${id}:${revision}`} id={id} onSubmitted={refresh} />
        )}
      </div>
    </section>
  );
}
