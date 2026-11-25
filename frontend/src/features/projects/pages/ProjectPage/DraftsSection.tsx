import { t } from "@/shared/i18n/t";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";
import { DraftCard } from "../../components/DraftCard";
import { copyText } from "../../clipboard";
import { useSaveDraft } from "../../hooks/useSaveDraft";
import type { DraftsRegeneration } from "../../hooks/useRegenerateDrafts";
import type { useProjectRun } from "../../hooks/useProjectRun";
import type { ProjectDetailView } from "../../toView";
import { RegenerateDrafts } from "./RegenerateDrafts";

interface DraftsSectionProps {
  projectId: string;
  drafts: ProjectDetailView["drafts"];
  /**
   * Without any draft (text like the profile entry), the section offers to rewrite them.
   */
  regenerable: boolean;
  regeneration: DraftsRegeneration;
  run: ReturnType<typeof useProjectRun>;
}

/**
 * January's drafts (CV line, LinkedIn post, README plan): editable,
 * « Enregistrer » (the server re-checks a draft to verify), « Copier » (rejected if the
 * clipboard fails, the card says so). The app publishes nothing. A validated project
 * with none (their write failed) offers « Régénérer les brouillons », then follows their
 * write; when it succeeds, the section title takes focus.
 */
export function DraftsSection(props: DraftsSectionProps) {
  const { projectId, drafts, regenerable, regeneration, run } = props;
  const { save, savingKind, error, errorKind } = useSaveDraft(projectId);
  // A write started here has succeeded once the drafts are there: the button and tracker that
  // had focus are unmounted, and the section title takes it back (once only).
  const written = regeneration.sessionId !== null && !regenerable;
  const title = useFocusOnMount<HTMLHeadingElement>(written);
  return (
    <section aria-labelledby="project-drafts" className="flex flex-col gap-3">
      <h2
        id="project-drafts"
        ref={title}
        tabIndex={-1}
        className="text-lg font-medium outline-none"
      >
        {t("projects.page.draftsTitle")}
      </h2>
      <p className="text-sm text-muted-foreground">
        {t(drafts.length === 0 ? "projects.page.draftsEmpty" : "projects.page.draftsText")}
      </p>
      {regenerable ? <RegenerateDrafts regeneration={regeneration} run={run} /> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {drafts.map((draft) => (
          <DraftCard
            key={draft.kind}
            draft={draft}
            saving={savingKind === draft.kind}
            error={errorKind === draft.kind ? error : null}
            onSave={(content) => save(draft.kind, content)}
            onCopy={copyText}
          />
        ))}
      </div>
    </section>
  );
}
