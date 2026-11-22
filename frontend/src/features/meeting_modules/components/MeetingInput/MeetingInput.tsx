import { useId, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  busy: boolean;
  onPrepare: (title: string, transcript: string) => void;
}

export function MeetingInput({ busy, onPrepare }: Props) {
  const hint = useId();
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (!busy)
      onPrepare(String(data.get("title") ?? "").trim(), String(data.get("transcript") ?? ""));
  }
  return (
    <form onSubmit={submit} className="grid gap-3">
      <label className="grid gap-1">
        {t("meetingModules.name")}
        <input className="rounded border bg-background p-2" name="title" required maxLength={140} />
      </label>
      <label className="grid gap-1">
        {t("meetingModules.transcript")}
        <textarea
          className="min-h-48 rounded border bg-background p-2"
          name="transcript"
          aria-describedby={hint}
          maxLength={16000}
          required
        />
      </label>
      <p className="text-sm" id={hint}>
        {t("meetingModules.transcriptHint")}
      </p>
      <Button type="submit" aria-disabled={busy}>
        {t("meetingModules.prepare")}
      </Button>
    </form>
  );
}
