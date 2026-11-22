import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { fetchTerminal, sendTerminal, startTerminal, stopTerminal } from "../terminalApi";
import { useRunPolling } from "./useRunPolling";

type Action = { kind: "start" } | { kind: "send"; data: string } | { kind: "stop" };

export function useTerminal(sessionId: string, save: () => Promise<boolean>) {
  const [id, setId] = useState<string | null>(null);
  const progress = useRunPolling(id, () => undefined, fetchTerminal);
  const action = useMutation({
    mutationFn: async (command: Action) => {
      if (command.kind === "start") {
        if (!(await save())) {
          throw new ApiError({
            code: "unsaved_files",
            status: 409,
            message: t("ide.project.saveFirst"),
          });
        }
        return (await startTerminal(sessionId)).id;
      }
      if (id) {
        if (command.kind === "send") await sendTerminal(id, command.data);
        else await stopTerminal(id);
      }
      return null;
    },
    onSuccess: (started) => {
      if (started) setId(started);
    },
  });
  return { progress, action };
}
