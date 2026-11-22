import type { FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ExperimentDraft } from "../viewTypes";
import { SourceFields } from "./SourceFields";

interface Props {
  pending: boolean;
  onCreate: (request: ExperimentDraft) => void;
}

function readRequest(form: FormData): ExperimentDraft {
  const text = (name: string) => String(form.get(name) ?? "").trim();
  const source = (side: "first" | "second") => ({
    url: text(`${side}-url`),
    version: text(`${side}-version`),
    claim: text(`${side}-claim`),
  });
  return {
    title: text("title"),
    first: source("first"),
    second: source("second"),
    protocol: text("protocol"),
    criterion: text("criterion"),
  };
}

export function ExperimentForm({ pending, onCreate }: Props) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onCreate(readRequest(new FormData(event.currentTarget)));
  }

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <label className="grid gap-1">
        {t("contradictoryWatch.name")}
        <input name="title" className="rounded border bg-background p-2" maxLength={140} required />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <SourceFields source="first" />
        <SourceFields source="second" />
      </div>
      <label className="grid gap-1">
        {t("contradictoryWatch.protocol")}
        <textarea
          name="protocol"
          className="rounded border bg-background p-2"
          maxLength={3000}
          required
        />
      </label>
      <label className="grid gap-1">
        {t("contradictoryWatch.criterion")}
        <textarea
          name="criterion"
          className="rounded border bg-background p-2"
          maxLength={3000}
          required
        />
      </label>
      <Button type="submit" disabled={pending}>
        {t("contradictoryWatch.save")}
      </Button>
    </form>
  );
}
