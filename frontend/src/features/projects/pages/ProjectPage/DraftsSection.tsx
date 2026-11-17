import { t } from "@/shared/i18n/t";
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
  /** Sans aucun brouillon (le texte comme l'entrée du profil), la section propose de les réécrire. */
  regenerable: boolean;
  regeneration: DraftsRegeneration;
  run: ReturnType<typeof useProjectRun>;
}

/**
 * Les brouillons au nom de January (ligne de CV, post LinkedIn, plan de README) : modifiables,
 * « Enregistrer » (le serveur recontrôle un brouillon à vérifier), « Copier » (rejeté si le
 * presse-papiers échoue, la carte le dit). Rien n'est publié par l'application. Un projet validé qui
 * n'en a pas (leur écriture a échoué) propose « Régénérer les brouillons », puis suit leur écriture.
 */
export function DraftsSection(props: DraftsSectionProps) {
  const { projectId, drafts, regenerable, regeneration, run } = props;
  const { save, savingKind, error, errorKind } = useSaveDraft(projectId);
  return (
    <section aria-labelledby="project-drafts" className="flex flex-col gap-3">
      <h2 id="project-drafts" className="text-lg font-medium">
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
