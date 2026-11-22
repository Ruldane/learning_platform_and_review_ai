import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  busy: boolean;
  canAdd: boolean;
  dirty: boolean;
  replay: boolean;
  add: (kind: "code" | "markdown") => void;
  save: () => void;
  setReplay: (value: boolean) => void;
}

export function NotebookToolbar({ busy, canAdd, dirty, replay, add, save, setReplay }: Props) {
  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy || !canAdd}
          onClick={() => add("code")}
        >
          {t("ide.notebook.addCode")}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={busy || !canAdd}
          onClick={() => add("markdown")}
        >
          {t("ide.notebook.addMarkdown")}
        </Button>
        <Button type="button" size="sm" disabled={busy || !dirty} onClick={save}>
          {t("ide.notebook.save")}
        </Button>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={replay}
          onChange={(event) => setReplay(event.target.checked)}
        />
        {t("ide.notebook.replay")}
      </label>
    </div>
  );
}
