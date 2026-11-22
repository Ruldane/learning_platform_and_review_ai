import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addFolder,
  changeFolder,
  deleteFolder,
  fetchFolders,
  fetchFolderStatus,
  type Folder,
} from "../api";

const KEYS = {
  folders: ["brain", "folders"],
  status: ["brain", "status"],
} as const;

export function useFolders(afterRemove: () => void) {
  const client = useQueryClient();
  const folders = useQuery({
    queryKey: KEYS.folders,
    queryFn: ({ signal }) => fetchFolders(signal),
  });
  const status = useQuery({
    queryKey: KEYS.status,
    queryFn: ({ signal }) => fetchFolderStatus(signal),
    refetchInterval: 5_000,
  });
  const update = (folder: Folder) => {
    client.setQueryData<Folder[]>(KEYS.folders, (saved = []) =>
      saved.some((item) => item.id === folder.id)
        ? saved.map((item) => (item.id === folder.id ? folder : item))
        : [...saved, folder],
    );
    void client.invalidateQueries({ queryKey: KEYS.status });
  };
  const add = useMutation({ mutationFn: addFolder, onSuccess: update });
  const toggle = useMutation({
    mutationFn: (folder: Folder) => changeFolder(folder.id, { paused: !folder.paused }),
    onSuccess: update,
  });
  const remove = useMutation({
    mutationFn: deleteFolder,
    onSuccess: (_, id) => {
      afterRemove();
      client.setQueryData<Folder[]>(KEYS.folders, (saved) =>
        saved?.filter((folder) => folder.id !== id),
      );
      void client.invalidateQueries({ queryKey: KEYS.status });
      void client.invalidateQueries({ queryKey: ["memory"] });
    },
  });
  return { folders, status, add, toggle, remove };
}
