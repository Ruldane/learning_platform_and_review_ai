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
   * Sans aucun brouillon (le texte comme l'entrée du profil), la section propose de les réécrire.
   */
  regenerable: boolean;
  regeneration: DraftsRegeneration;
  run: ReturnType<typeof useProjectRun>;
}

/**
 * Les brouillons au nom de January (ligne de CV, post LinkedIn, plan de README) : modifiables,
 * « Enregistrer » (le serveur recontrôle un brouillon à vérifier), « Copier » (rejeté si le
 * presse-papiers échoue, la carte le dit). Rien n'est publié par l'application. Un projet validé
 * qui n'en a pas (leur écriture a échoué) propose « Régénérer les brouillons », puis suit leur
 * écriture ; quand elle aboutit, le titre de la section prend le focus.
 */
export function DraftsSection(props: DraftsSectionProps) {
  const { projectId, drafts, regenerable, regeneration, run } = props;
  const { save, savingKind, error, errorKind } = useSaveDraft(projectId);
  // Une écriture lancée d'ici a abouti quand les brouillons sont là : le bouton et le suivi qui
  // avaient le focus sont démontés, le titre de la section le reprend (une seule fois).
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
