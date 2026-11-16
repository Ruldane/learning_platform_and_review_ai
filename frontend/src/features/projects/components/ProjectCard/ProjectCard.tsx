import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { ProjectCardView } from "../viewTypes";

interface ProjectCardProps {
  project: ProjectCardView;
}

/** Une carte du Portfolio : titre (lien vers la page du projet s'il y en a une), statut écrit, heures. */
export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <article
      data-status={project.status}
      className="flex flex-col gap-1.5 rounded-xl border bg-card p-4 text-sm"
    >
      <h3 className="text-base font-medium">
        {project.href ? (
          <Link to={project.href} className="text-primary underline underline-offset-4">
            {project.title}
          </Link>
        ) : (
          project.title
        )}
      </h3>
      <p className="font-medium">
        {t("projects.card.statusLabel", { status: t(`projects.card.status.${project.status}`) })}
      </p>
      {project.hours !== null ? (
        <p className="text-muted-foreground tabular-nums">
          {t("projects.card.hours", { hours: project.hours })}
        </p>
      ) : null}
      {project.skills.length > 0 ? (
        <p className="text-muted-foreground">
          {t("projects.card.skills", { skills: project.skills.join(", ") })}
        </p>
      ) : null}
    </article>
  );
}
