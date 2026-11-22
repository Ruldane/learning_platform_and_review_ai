import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { meetingsKey, publishMeeting, readMeeting, setSelection } from "../../api";
import { ExcerptChooser } from "../../components/ExcerptChooser";
import { StudySequence } from "../../components/StudySequence";

type Module = Awaited<ReturnType<typeof readMeeting>>;

function useModuleActions(id: string) {
  const cache = useQueryClient();
  const save = (value: Module) => cache.setQueryData([...meetingsKey, id], value);
  const preview = useMutation({
    mutationFn: (lines: number[]) => setSelection(id, lines),
    onSuccess: save,
  });
  const publish = useMutation({
    mutationFn: (lines: number[]) => publishMeeting(id, lines),
    onSuccess: (value) => {
      void cache.invalidateQueries({ queryKey: meetingsKey });
      save(value);
    },
  });
  return {
    preview,
    publish,
    busy: preview.isPending || publish.isPending,
    error: preview.error ?? publish.error,
  };
}

export function MeetingWorkspace({ module }: { module: Module }) {
  const [selection, setSelection] = useState(module.selection);
  const { preview, publish, busy, error } = useModuleActions(module.id);
  const frozen = module.status === "published";
  const aligned =
    selection.length === module.selection.length &&
    selection.every((line, index) => line === module.selection[index]);

  return (
    <>
      <h1 className="text-2xl font-semibold">{module.title}</h1>
      <p
        role="status"
        tabIndex={-1}
        ref={publish.isSuccess ? (status) => status?.focus() : undefined}
      >
        {t(`meetingModules.${module.status}`)}
      </p>
      {error && <InlineError message={errorMessage(error)} />}
      {!frozen && (
        <ExcerptChooser
          excerpts={module.excerpts}
          selection={selection}
          busy={busy}
          onToggle={(line) =>
            setSelection((previous) =>
              previous.includes(line)
                ? previous.filter((item) => item !== line)
                : [...previous, line],
            )
          }
          onPreview={() => preview.mutate(selection)}
        />
      )}
      <StudySequence steps={module.steps} excerpts={module.excerpts} />
      {!frozen && aligned && module.steps.length > 0 && (
        <Button
          type="button"
          aria-disabled={busy}
          onClick={() => !busy && publish.mutate(selection)}
        >
          {t("meetingModules.save")}
        </Button>
      )}
      <p className="break-all text-sm">
        {t("meetingModules.snapshot")} <code>{module.source_digest}</code>
      </p>
    </>
  );
}
