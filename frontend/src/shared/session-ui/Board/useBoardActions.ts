import { useCallback, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { BoardEdit } from "../boardTypes";
import { annotationNote } from "./annotationNote";
import type { BoardApi } from "./boardApi";
import { exportBoard, serializeScene, type ExportFormat } from "./exportBoard";
import type { useBoardEdits } from "./useBoardEdits";

interface Options {
  boardId: string;
  title: string;
  edits: ReturnType<typeof useBoardEdits>;
  onSendEdit: (boardId: string, edit: BoardEdit) => void | Promise<void>;
}

/** Les deux actions de la barre : exporter le tableau, envoyer les modifications aux agents. */
export function useBoardActions({ boardId, title, edits, onSendEdit }: Options) {
  const [api, setApi] = useState<BoardApi | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exportAs = useCallback(
    async (format: ExportFormat) => {
      if (!api) return;
      setError(null);
      try {
        await exportBoard(format, api, title);
      } catch {
        setError(t("session.board.exportFailed"));
      }
    },
    [api, title],
  );

  const send = useCallback(async () => {
    if (!api) return;
    setError(null);
    try {
      const { before, after } = edits.snapshot();
      const note = annotationNote(before, after) || t("session.board.genericNote");
      await onSendEdit(boardId, { scene: await serializeScene(api), note });
      edits.markSent();
    } catch {
      // La page qui envoie affiche sa propre erreur ; le bouton reste actif pour réessayer.
      setError(t("session.board.sendFailed"));
    }
  }, [api, boardId, edits, onSendEdit]);

  return { api, setApi, error, exportAs, send };
}
