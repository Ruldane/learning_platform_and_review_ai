import { useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ReadingSourceInput } from "../../api";
import { SourceFields } from "./SourceFields";

export function SourceForm({
  busy,
  onCreate,
}: {
  busy: boolean;
  onCreate: (body: ReadingSourceInput) => Promise<boolean>;
}) {
  const [form, setForm] = useState<ReadingSourceInput>({ kind: "topic", label: "", value: "" });
  const field = useRef<HTMLInputElement>(null);
  const { label, value } = form;
  const submit = async () => {
    if (busy || !label.trim() || !value.trim()) return;
    if (await onCreate({ ...form, label: label.trim(), value: value.trim() })) {
      setForm({ ...form, label: "", value: "" });
      field.current?.focus();
    }
  };
  return (
    <form
      className="grid gap-3 sm:grid-cols-2"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <SourceFields value={form} onChange={setForm} labelRef={field} />
      <Button
        type="submit"
        className="justify-self-start"
        disabled={busy || !label.trim() || !value.trim()}
      >
        {t("reading.sources.add")}
      </Button>
    </form>
  );
}
