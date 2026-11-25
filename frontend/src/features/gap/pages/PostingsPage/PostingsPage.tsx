import { useRef, useState, type ComponentType } from "react";
import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { PostingForm } from "../../components/PostingForm";
import { useCreatePosting } from "../../hooks/useCreatePosting";
import { ANALYSIS_POLL_MS } from "../../hooks/usePostings";
import type { PostingCreatedOut } from "../../types";
import { ExistingPosting } from "./ExistingPosting";
import { PostingsListPanel } from "./PostingsListPanel";

interface PostingsPageProps {
  /** List re-read interval, in ms (shortened by tests). */
  pollMs?: number;
  offersChat?: ComponentType;
}

const FIELD = '[role="tabpanel"]:not([hidden]) :is(input, textarea)';

/**
 * Postings (`/career/postings`): the add form at the top, then the list. A new posting
 * (201) opens its page; a posting already added (200) is announced with a link, without
 * a duplicate in the list.
 */
export function PostingsPage({
  pollMs = ANALYSIS_POLL_MS,
  offersChat: OffersChat,
}: PostingsPageProps) {
  const navigate = useNavigate();
  const formRoot = useRef<HTMLDivElement>(null);
  const [existing, setExisting] = useState<PostingCreatedOut | null>(null);
  const create = useCreatePosting((result) => {
    if (result.created) void navigate(`/career/postings/${result.posting.id}`);
    else setExisting(result);
  });

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">{t("gap.postings.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("gap.postings.intro")}</p>
        </div>
        {OffersChat ? <OffersChat /> : null}
      </header>
      <div ref={formRoot} className="flex flex-col gap-3">
        <PostingForm
          pending={create.pending}
          error={create.error}
          launchOptions={create.providerMenu}
          onSubmit={(source) => {
            setExisting(null);
            create.create(source);
          }}
        />
        {existing ? <ExistingPosting result={existing} /> : null}
      </div>
      <PostingsListPanel
        pollMs={pollMs}
        onAdd={() => formRoot.current?.querySelector<HTMLElement>(FIELD)?.focus()}
      />
    </div>
  );
}
