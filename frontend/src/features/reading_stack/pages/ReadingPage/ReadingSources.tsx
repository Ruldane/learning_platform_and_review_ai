import { useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSources } from "../../hooks/useSources";
import { SourceForm } from "./SourceForm";
import { SourceRow } from "./SourceRow";

export function ReadingSources() {
  const [open, setOpen] = useState(false);
  const summary = useRef<HTMLElement>(null);
  const { query, add, toggle, remove, error, busy } = useSources(open, () =>
    summary.current?.focus(),
  );
  return (
    <details
      className="rounded-xl border p-3"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary ref={summary} className="cursor-pointer font-medium">
        {t("reading.sources.title")}
      </summary>
      {open ? (
        <div className="mt-3 flex flex-col gap-3">
          <SourceForm
            busy={busy}
            onCreate={(body) =>
              add.mutateAsync(body).then(
                () => true,
                () => false,
              )
            }
          />
          {error ? <InlineError message={errorMessage(error)} /> : null}
          {query.isPending ? <LoadingState label={t("reading.sources.load")} /> : null}
          {query.data?.length === 0 ? (
            <p className="text-sm">{t("reading.sources.empty")}</p>
          ) : null}
          <ul className="grid gap-2 sm:grid-cols-2">
            {query.data?.map((source) => (
              <SourceRow
                key={source.id}
                source={source}
                busy={busy}
                onToggle={() => toggle.mutate({ id: source.id, active: !source.active })}
                onRemove={() => remove.mutate(source.id)}
              />
            ))}
          </ul>
        </div>
      ) : null}
    </details>
  );
}
