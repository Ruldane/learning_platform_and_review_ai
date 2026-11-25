import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { useLaunchSource } from "@/shared/session-ui";
import { importProfile, type ProfileImport } from "../api";

/**
 * `POST /profile/import` from the first run: the reading happens in the background on the
 * server, the step waits for nothing but the acknowledgement. A failure keeps its message
 * (409: a reading is already in progress; 413 and 415: the file); sending again clears it.
 */
export function useImportProfile() {
  const provider = useLaunchSource();
  const mutation = useMutation({
    mutationFn: (documents: ProfileImport) => importProfile(documents, provider.source),
  });
  const { mutate, reset } = mutation;
  return {
    start: (documents: ProfileImport) => {
      reset();
      mutate(documents);
    },
    launchMenu: provider.menu,
    pending: mutation.isPending,
    imported: mutation.isSuccess,
    error: mutation.isError ? errorMessage(mutation.error) : null,
  };
}
