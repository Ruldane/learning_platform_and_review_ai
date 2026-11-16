import { t } from "@/shared/i18n/t";
import { DraftCard } from "../../components/DraftCard";
import { copyText } from "../../clipboard";
import { useSaveDraft } from "../../hooks/useSaveDraft";
import type { ProjectDetailView } from "../../toView";

interface DraftsSectionProps {
  projectId: string;
  drafts: ProjectDetailView["drafts"];
}

/**
 * Les brouillons au nom de January (ligne de CV, post LinkedIn, plan de README) : modifiables,
 * « Enregistrer » (le serveur recontrôle un brouillon à vérifier), « Copier » (rejeté si le
 * presse-papiers échoue, la carte le dit). Rien n'est publié par l'application.
 */
export function DraftsSection({ projectId, drafts }: DraftsSectionProps) {
  const { save, savingKind, error, errorKind } = useSaveDraft(projectId);
  const empty = drafts.length === 0;
  return (
    <section aria-labelledby="project-drafts" className="flex flex-col gap-3">
      <h2 id="project-drafts" className="text-lg font-medium">
        {t("projects.page.draftsTitle")}
      </h2>
      <p className="text-sm text-muted-foreground">
        {t(empty ? "projects.page.draftsEmpty" : "projects.page.draftsText")}
      </p>
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
