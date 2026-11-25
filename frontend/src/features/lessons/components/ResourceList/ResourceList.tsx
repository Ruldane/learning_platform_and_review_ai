import { t } from "@/shared/i18n/t";
import type { ResourceView } from "../viewTypes";
import { ResourceItem } from "./ResourceItem";

interface ResourceListProps {
  resources: ResourceView[];
  /** Asks for the new resource status (« Lue » or « À lire »). */
  onToggleStatus: (resourceId: string, status: ResourceView["status"]) => void;
}

/** The resources of a lesson or of the library, with their reading status. */
export function ResourceList({ resources, onToggleStatus }: ResourceListProps) {
  return (
    <ul aria-label={t("lessons.resources.heading")} className="flex flex-col gap-3">
      {resources.map((resource) => (
        <ResourceItem key={resource.id} resource={resource} onToggleStatus={onToggleStatus} />
      ))}
    </ul>
  );
}
