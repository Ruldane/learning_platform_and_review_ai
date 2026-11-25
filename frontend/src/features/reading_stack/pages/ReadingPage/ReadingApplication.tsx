import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { createReadingApplication } from "../../api";

export function ReadingApplication({ id, company }: { id: string; company: string | null }) {
  const [name, setName] = useState(company ?? "");
  const save = useMutation({ mutationFn: () => createReadingApplication(id, name.trim()) });
  return (
    <details className="rounded-md border p-3">
      <summary className="cursor-pointer text-sm font-medium">
        {t("reading.actions.application")}
      </summary>
      <form
        className="mt-3 flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim() && !save.isPending) save.mutate();
        }}
      >
        <label className="flex flex-col gap-1 text-sm">
          {t("reading.actions.company")}
          <input
            className="rounded-md border bg-background p-2"
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <Button type="submit" className="self-start" disabled={!name.trim() || save.isPending}>
          {t("reading.actions.confirm")}
        </Button>
        {save.data ? (
          <Link
            className="self-start text-sm underline"
            to={`/applications/${save.data.application_id}`}
          >
            {t("reading.actions.openApplication")}
          </Link>
        ) : null}
        {save.error ? <InlineError message={errorMessage(save.error)} /> : null}
      </form>
    </details>
  );
}
