import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Folder, FolderPatch, FolderStatus } from "../../api";
import { FolderExclusions } from "./FolderExclusions";
import { ImportReport } from "./ImportReport";
import { RemoveFolder } from "./RemoveFolder";

interface FolderCardProps {
  folder: Folder;
  status?: FolderStatus;
  busy: boolean;
  onToggle: () => void;
  onRemove: () => void;
  onFilter: (patch: FolderPatch) => void;
}

export function FolderCard({ folder, status, busy, onToggle, onRemove, onFilter }: FolderCardProps) {
  const title = useId();
  return (
    <article aria-labelledby={title} className="grid gap-3 rounded-xl border border-border p-4">
      <div>
        <h3 id={title} className="font-semibold">
          {folder.name}
        </h3>
        <p className="text-sm break-all text-muted-foreground">{folder.path}</p>
      </div>
      <ImportReport status={status} />
      <FolderExclusions folder={folder} busy={busy} onSave={onFilter} />
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="outline" disabled={busy} onClick={onToggle}>
          {t(folder.paused ? "brain.resume" : "brain.pause")}
        </Button>
        <RemoveFolder name={folder.name} busy={busy} onRemove={onRemove} />
      </div>
    </article>
  );
}
