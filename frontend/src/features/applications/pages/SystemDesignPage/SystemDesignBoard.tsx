import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Board, type BoardEdit, type BoardStateView } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import { saveDesignBoard, type Design } from "../../systemDesignApi";

interface Props {
  board: Design["board"];
  readOnly: boolean;
  onBoardSaved: (board: Design["board"]) => void;
  onDirtyChange: (dirty: boolean) => void;
}

const read: (row: Design["board"]) => BoardStateView = (row) => ({
  id: row.id,
  kind: row.kind,
  title: row.title,
  step: row.step,
  mermaid: row.mermaid,
  scene: row.scene,
  author: row.author,
  createdAt: row.created_at,
});

export function SystemDesignBoard({ board, readOnly, onBoardSaved, onDirtyChange }: Props) {
  const edit = useMutation({
    mutationFn: ([id, draft]: [string, BoardEdit]) => saveDesignBoard(id, draft),
    onSuccess: onBoardSaved,
  });
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <p>
        {t(readOnly ? "systemDesign.frozenVersion" : "systemDesign.savedVersion", {
          version: board.step,
        })}
      </p>
      <Board
        states={[read(board)]}
        activeId={board.id}
        onSelect={() => undefined}
        readOnly={readOnly}
        sending={edit.isPending}
        onDirtyChange={onDirtyChange}
        onSendEdit={async (id, draft) => {
          await edit.mutateAsync([id, draft]);
        }}
        labels={{
          label: t("systemDesign.board"),
          empty: t("systemDesign.empty"),
          drawing: t("systemDesign.boardLoading"),
          save: t("systemDesign.save"),
        }}
      />
      {edit.error && <InlineError message={errorMessage(edit.error)} />}
    </div>
  );
}
