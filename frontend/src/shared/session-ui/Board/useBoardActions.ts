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

/**
 * The two actions of the bar: export the board (its failure is said in `error`), send
 * changes to the agents (its failure is said on the page, which sends).
 */
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
    const { before, after } = edits.snapshot();
    const note = annotationNote(before, after) || t("session.board.genericNote");
    let scene: Record<string, unknown>;
    try {
      scene = await serializeScene(api);
    } catch {
      // Local failure, before any sending: only the board can say so.
      return setError(t("session.board.sendFailed"));
    }
    try {
      await onSendEdit(boardId, { scene, note });
      edits.markSent();
    } catch {
      // Sending failed: the page that sends reports it (once, with the server's message);
      // the button stays active to retry.
    }
  }, [api, boardId, edits, onSendEdit]);

  return { api, setApi, error, exportAs, send };
}
