import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { PostingForm } from "../../components/PostingForm";
import { useCreatePosting } from "../../hooks/useCreatePosting";
import { ANALYSIS_POLL_MS } from "../../hooks/usePostings";
import type { PostingCreatedOut } from "../../types";
import { ExistingPosting } from "./ExistingPosting";
import { PostingsListPanel } from "./PostingsListPanel";

interface PostingsPageProps {
  /** Intervalle de relecture de la liste, en ms (réduit par les tests). */
  pollMs?: number;
}

const FIELD = '[role="tabpanel"]:not([hidden]) :is(input, textarea)';

/**
 * Les offres (`/carriere/offres`) : le formulaire d'ajout en tête, puis la liste. Une offre
 * nouvelle (201) ouvre sa page ; une offre déjà ajoutée (200) est annoncée avec un lien, sans
 * doublon dans la liste.
 */
export function PostingsPage({ pollMs = ANALYSIS_POLL_MS }: PostingsPageProps) {
  const navigate = useNavigate();
  const formRoot = useRef<HTMLDivElement>(null);
  const [existing, setExisting] = useState<PostingCreatedOut | null>(null);
  const create = useCreatePosting((result) => {
    if (result.created) void navigate(`/carriere/offres/${result.posting.id}`);
    else setExisting(result);
  });

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t("gap.postings.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("gap.postings.intro")}</p>
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
