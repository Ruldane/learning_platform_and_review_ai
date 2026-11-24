import { useMutation } from "@tanstack/react-query";
import { useId, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ConversationList } from "../../components/ConversationList";
import { useConversationList } from "../../hooks/useConversationList";
import { createOffersThread } from "../../offersApi";
import { OffersThread } from "./OffersThread";

function useOffersSelection(onSelected: () => void) {
  const [requested, setRequested] = useState<string | null>(null);
  const [showList, setShowList] = useState(false);
  const [revision, setRevision] = useState(0);
  const { sidebar, refresh, listPending } = useConversationList("offers", (action) => {
    if (action.kind === "clear") setRevision((value) => value + 1);
    if (action.kind === "delete" || action.kind === "wipe") setRequested(null);
  });
  const select = (id: string) => {
    setRequested(id);
    setShowList(false);
    requestAnimationFrame(onSelected);
  };
  const create = useMutation({
    mutationFn: createOffersThread,
    onSuccess: (thread) => {
      select(thread.id);
      refresh();
    },
  });
  return {
    id: requested ?? sidebar.entries[0]?.id ?? null,
    sidebar,
    refresh,
    listPending,
    showList,
    setShowList,
    revision,
    select,
    create,
  };
}

export function OffersChatPanel() {
  const threadFocus = useRef<HTMLDivElement>(null);
  const state = useOffersSelection(() => threadFocus.current?.focus());
  const listId = useId();
  const { id, sidebar, create, showList, setShowList } = state;
  return (
    <div
      className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3 p-3
      md:grid-cols-[15rem_minmax(0,1fr)] md:grid-rows-[minmax(0,1fr)] md:gap-4 md:p-4"
    >
      <Button
        variant="outline"
        size="sm"
        className="justify-self-start md:hidden"
        aria-controls={listId}
        aria-expanded={showList}
        onClick={() => setShowList(!showList)}
      >
        {t(showList ? "conversations.offers.back" : "conversations.offers.chats")}
      </Button>
      <div id={listId} className={cn("min-h-0 overflow-y-auto md:block", !showList && "hidden")}>
        <ConversationList
          {...sidebar}
          selected={id}
          createLabel={t("conversations.offers.newChat")}
          busy={sidebar.busy || create.isPending}
          error={create.error ? errorMessage(create.error) : sidebar.error}
          onCreate={() => create.mutate()}
          onSelect={state.select}
        />
      </div>
      <div
        ref={threadFocus}
        tabIndex={-1}
        className={cn("min-h-0 min-w-0 flex-col md:flex", showList ? "hidden" : "flex")}
      >
        {id ? (
          <OffersThread key={`${id}:${state.revision}`} id={id} onSubmitted={state.refresh} />
        ) : state.listPending ? (
          <LoadingState label={t("conversations.loading")} />
        ) : (
          <p className="m-auto text-center text-sm text-muted-foreground">
            {t("conversations.offers.empty")}
          </p>
        )}
      </div>
    </div>
  );
}
