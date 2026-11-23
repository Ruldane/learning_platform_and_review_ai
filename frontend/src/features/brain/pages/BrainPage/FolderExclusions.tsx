import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Folder, FolderPatch } from "../../api";

const lines = (value: string) => value.split("\n").map((line) => line.trim()).filter(Boolean);

export function FolderExclusions({ folder, busy, onSave }: {
  folder: Folder; busy: boolean; onSave: (body: FolderPatch) => void;
}) {
  const id = useId();
  const [directories, setDirectories] = useState(folder.excluded_directories?.join("\n") ?? "");
  const [extensions, setExtensions] = useState(folder.excluded_extensions?.join("\n") ?? "");
  return (
    <details className="rounded-md bg-muted p-2">
      <summary className="cursor-pointer text-sm font-medium">{t("brain.exclusions.title")}</summary>
      <form className="mt-3 grid gap-3" onSubmit={(event) => {
        event.preventDefault();
        if (!busy) onSave({ excluded_directories: lines(directories), excluded_extensions: lines(extensions) });
      }}>
        <p id={`${id}-help`} className="text-sm">{t("brain.exclusions.help")}</p>
        <label className="grid gap-1 text-sm">
          {t("brain.exclusions.directories")}
          <textarea rows={3} value={directories} aria-describedby={`${id}-help`}
            onChange={(event) => setDirectories(event.target.value)}
            className="rounded-md border bg-background p-2" />
        </label>
        <label className="grid gap-1 text-sm">
          {t("brain.exclusions.extensions")}
          <textarea rows={3} value={extensions} aria-describedby={`${id}-help`}
            onChange={(event) => setExtensions(event.target.value)}
            className="rounded-md border bg-background p-2" />
        </label>
        <Button type="submit" variant="outline" size="sm" className="justify-self-start" aria-disabled={busy}>
          {t("brain.exclusions.save")}
        </Button>
      </form>
    </details>
  );
}
