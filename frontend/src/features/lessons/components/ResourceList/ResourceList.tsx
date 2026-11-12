import { t } from "@/shared/i18n/t";
import type { ResourceView } from "../viewTypes";
import { ResourceItem } from "./ResourceItem";

interface ResourceListProps {
  resources: ResourceView[];
  /** Demande le nouveau statut de la ressource (« Lue » ou « À lire »). */
  onToggleStatus: (resourceId: string, status: ResourceView["status"]) => void;
}

/** Les ressources d'une leçon ou de la bibliothèque, avec leur statut de lecture. */
export function ResourceList({ resources, onToggleStatus }: ResourceListProps) {
  return (
    <ul aria-label={t("lessons.resources.heading")} className="flex flex-col gap-3">
      {resources.map((resource) => (
        <ResourceItem key={resource.id} resource={resource} onToggleStatus={onToggleStatus} />
      ))}
    </ul>
  );
}
