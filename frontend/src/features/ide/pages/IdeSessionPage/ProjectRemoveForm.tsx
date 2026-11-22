import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { FormProps } from "./ProjectFileForms";

interface RemoveProps extends FormProps {
  entry: string;
  paths: string[];
}

export function ProjectRemoveForm({ path, entry, paths, busy, cancel, submit }: RemoveProps) {
  const [replacement, setReplacement] = useState("");
  const escape = useRef<HTMLButtonElement>(null);
  const isEntry = path === entry;
  const options = paths.filter((name) => name !== path);
  useEffect(() => escape.current?.focus(), []);
  return (
    <form
      className="grid gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy && (!isEntry || replacement)) {
          submit({ kind: "remove", path, replacementEntry: replacement || undefined });
        }
      }}
    >
      <p className="text-sm">{t("ide.project.confirm", { path })}</p>
      {isEntry ? (
        <label className="grid gap-1 text-sm">
          {t("ide.project.newEntry")}
          <select
            required
            value={replacement}
            onChange={(event) => setReplacement(event.target.value)}
            className="rounded border border-border p-1 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">{t("ide.project.chooseEntry")}</option>
            {options.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button disabled={busy || (isEntry && !replacement)} variant="destructive" type="submit">
          {t("ide.project.remove")}
        </Button>
        <Button ref={escape} disabled={busy} variant="outline" type="button" onClick={cancel}>
          {t("ide.project.cancel")}
        </Button>
      </div>
    </form>
  );
}
