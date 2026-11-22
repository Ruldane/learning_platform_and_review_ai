import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { readReplay, replayKey, saveNote } from "../../api";
import { Annotation } from "../../components/Annotation";
import { Timeline } from "../../components/Timeline";

type Replay = Awaited<ReturnType<typeof readReplay>>;

export function ReplayWorkspace({ replay }: { replay: Replay }) {
  const [position, setPosition] = useState(replay.notes.at(-1)?.step ?? 0);
  const cache = useQueryClient();
  const record = useMutation({
    mutationFn: (hypothesis: string) => saveNote(replay.id, { step: position, hypothesis }),
    onSuccess: (current) => cache.setQueryData([...replayKey, replay.id], current),
  });
  return (
    <>
      <h1 className="text-2xl font-semibold">{replay.title}</h1>
      <Timeline events={replay.timeline} position={position} onSeek={setPosition} />
      {record.isError && <InlineError message={errorMessage(record.error)} />}
      <Annotation pending={record.isPending} saved={record.isSuccess} onSave={record.mutate} />
      {replay.notes.length > 0 && (
        <section className="grid gap-2">
          <h2 className="font-semibold">{t("incidentReplay.notes")}</h2>
          <ul className="grid gap-2">
            {replay.notes.map((note) => (
              <li className="rounded border p-3" key={JSON.stringify([note.step, note.hypothesis])}>
                <span className="text-sm text-muted-foreground">
                  {t("incidentReplay.minute", { value: replay.timeline[note.step]?.minute ?? 0 })}
                </span>
                <p className="whitespace-pre-wrap break-words">{note.hypothesis}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
