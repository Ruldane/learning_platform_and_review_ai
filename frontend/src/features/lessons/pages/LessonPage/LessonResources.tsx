import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ResourceList } from "../../components/ResourceList";
import type { ResourceView } from "../../components/viewTypes";
import type { useResourceStatus } from "../../hooks/useResourceStatus";

interface LessonResourcesProps {
  resources: ResourceView[];
  status: ReturnType<typeof useResourceStatus>;
}

/** Les ressources du module : « Lue » ou « À lire » se bascule ici. */
export function LessonResources({ resources, status }: LessonResourcesProps) {
  return (
    <section aria-labelledby="lesson-resources-title" className="flex flex-col gap-3">
      <h2 id="lesson-resources-title" className="text-xl font-semibold">
        {t("lessons.resources.heading")}
      </h2>
      {status.error ? <InlineError message={status.error} /> : null}
      {resources.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("lessons.resources.empty")}</p>
      ) : (
        <ResourceList resources={resources} onToggleStatus={status.setStatus} />
      )}
    </section>
  );
}
