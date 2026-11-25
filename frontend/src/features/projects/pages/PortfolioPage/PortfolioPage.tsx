import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ProjectCard } from "../../components/ProjectCard";
import { useProjects } from "../../hooks/useProjects";
import { groupByStatus } from "../../toView";

/**
 * Le Portfolio (`/skills/portfolio`) : un mini projet par module du programme, groupés par
 * statut (ce qui attend January d'abord) ; chaque carte mène à la page du projet.
 */
export function PortfolioPage() {
  const projects = useProjects();
  const groups = projects.data ? groupByStatus(projects.data) : [];
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t("projects.portfolio.title")}</h1>
        <p className="max-w-prose text-sm text-muted-foreground">{t("projects.portfolio.intro")}</p>
      </header>
      {projects.isPending ? <LoadingState label={t("projects.portfolio.loading")} /> : null}
      {projects.isError ? (
        <ErrorState
          message={errorMessage(projects.error)}
          onRetry={() => void projects.refetch()}
        />
      ) : null}
      {projects.data && groups.length === 0 ? (
        <EmptyState
          title={t("projects.portfolio.emptyTitle")}
          description={t("projects.portfolio.emptyText")}
        />
      ) : null}
      {groups.map((group) => (
        <section
          key={group.status}
          aria-labelledby={`portfolio-${group.status}`}
          className="flex flex-col gap-3"
        >
          <h2 id={`portfolio-${group.status}`} className="text-lg font-medium">
            {t(`projects.portfolio.groups.${group.status}`)}
          </h2>
          <ul className="grid gap-3 md:grid-cols-2">
            {group.projects.map((project) => (
              <li key={project.id}>
                <ProjectCard project={project} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
