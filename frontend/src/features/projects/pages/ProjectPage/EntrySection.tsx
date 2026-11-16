import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { DraftNotice } from "../../components/DraftCard";
import { ProfileEntryForm } from "../../components/ProfileEntryForm";
import { useAddToProfile } from "../../hooks/useAddToProfile";
import { PROFILE_PATH } from "../../paths";
import type { ProjectDetailView } from "../../toView";

/**
 * L'ajout du projet au profil maître : l'entrée proposée (modifiable), son avertissement « à
 * vérifier », puis « Ajouter au profil maître » ; une fois ajoutée, « Ajouté au profil (version N) »
 * remplace le bouton (et l'avertissement, devenu sans objet, disparaît). Rien n'entre dans le profil sans ce clic. Le formulaire ne lit son entrée
 * qu'une fois : sa `key` la suit.
 */
export function EntrySection({ project }: { project: ProjectDetailView }) {
  const { add, pending, failure } = useAddToProfile(project.id);
  return (
    <section aria-labelledby="project-entry" className="flex flex-col gap-3">
      <h2 id="project-entry" className="text-lg font-medium">
        {t("projects.page.entryTitle")}
      </h2>
      {project.entryDraft && project.profileVersion === null ? (
        <DraftNotice draft={project.entryDraft} />
      ) : null}
      <ProfileEntryForm
        key={JSON.stringify(project.entry)}
        entry={project.entry}
        added={project.profileVersion !== null}
        version={project.profileVersion}
        busy={pending}
        onAdd={add}
      />
      {failure ? (
        <div role="alert" className="flex flex-col gap-1 text-sm text-destructive">
          <p>{failure.message}</p>
          {failure.profileLink ? (
            <Link to={PROFILE_PATH} className="text-primary underline underline-offset-4">
              {t("projects.errors.profileLink")}
            </Link>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
