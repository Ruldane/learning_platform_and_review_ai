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
 * Les deux actions de la barre : exporter le tableau (son échec se dit dans `error`), envoyer les
 * modifications aux agents (son échec se dit sur la page, qui envoie).
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
      // Échec local, avant tout envoi : seul le tableau peut le dire.
      return setError(t("session.board.sendFailed"));
    }
    try {
      await onSendEdit(boardId, { scene, note });
      edits.markSent();
    } catch {
      // L'envoi a échoué : la page qui envoie le dit (une seule fois, avec le message du
      // serveur) ; le bouton reste actif pour réessayer.
    }
  }, [api, boardId, edits, onSendEdit]);

  return { api, setApi, error, exportAs, send };
}
