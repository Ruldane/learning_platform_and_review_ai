import { useEffect, useId, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ProjectCommand } from "../../projectApi";

export interface FormProps {
  path: string;
  busy: boolean;
  cancel: () => void;
  submit: (command: ProjectCommand) => void;
}

export function ProjectPathForm(props: FormProps & { mode: "create" | "rename" }) {
  const { mode, path, busy, cancel, submit } = props;
  const [name, setName] = useState(mode === "rename" ? path : "");
  const field = useRef<HTMLInputElement>(null);
  const id = useId();
  const wanted = name.trim();
  useEffect(() => field.current?.focus(), []);
  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy && wanted)
          submit(
            mode === "create"
              ? { kind: "create", path: wanted }
              : { kind: "rename", path, destination: wanted },
          );
      }}
    >
      <label htmlFor={id} className="grid flex-1 gap-1 text-sm">
        {t("ide.project.path")}
        <input
          id={id}
          ref={field}
          value={name}
          maxLength={200}
          className="rounded-md border border-border bg-background p-1.5 focus-visible:ring-2 focus-visible:ring-ring"
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      <Button disabled={busy || !wanted} type="submit">
        {t(mode === "create" ? "ide.project.add" : "ide.project.rename")}
      </Button>
      <Button variant="outline" disabled={busy} type="button" onClick={cancel}>
        {t("ide.project.cancel")}
      </Button>
    </form>
  );
}
