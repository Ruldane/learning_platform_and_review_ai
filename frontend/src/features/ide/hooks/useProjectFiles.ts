import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { editProjectFile, type ProjectCommand } from "../projectApi";
import { ideKeys } from "../queryKeys";
import type { IdeSession } from "../types";

export function useProjectFiles(
  session: IdeSession,
  save: () => Promise<boolean>,
  onChanged: (updated: IdeSession, command: ProjectCommand) => void,
) {
  const cache = useQueryClient();
  const key = ideKeys.session(session.id);
  return useMutation({
    scope: { id: `ide-project-${session.id}` },
    mutationFn: async (command: ProjectCommand) => {
      if (!(await save())) {
        throw new ApiError({
          code: "unsaved_files",
          status: 409,
          message: t("ide.project.saveFirst"),
        });
      }
      const current = cache.getQueryData<IdeSession>(key) ?? session;
      return editProjectFile(session.id, current.files_version ?? 0, command);
    },
    onSuccess: (updated, command) => {
      cache.setQueryData(key, updated);
      onChanged(updated, command);
    },
  });
}
