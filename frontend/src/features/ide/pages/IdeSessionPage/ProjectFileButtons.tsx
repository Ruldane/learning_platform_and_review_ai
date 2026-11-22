import type { Ref } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ProjectCommand } from "../../projectApi";

interface Props {
  trigger: Ref<HTMLButtonElement>;
  busy: boolean;
  canRemove: boolean;
  onChoose: (kind: ProjectCommand["kind"]) => void;
}

export function ProjectFileButtons({ trigger, busy, canRemove, onChoose }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        ref={trigger}
        size="sm"
        variant="outline"
        disabled={busy}
        onClick={() => onChoose("create")}
      >
        {t("ide.project.create")}
      </Button>
      <Button size="sm" variant="outline" disabled={busy} onClick={() => onChoose("rename")}>
        {t("ide.project.rename")}
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={busy || !canRemove}
        onClick={() => onChoose("remove")}
      >
        {t("ide.project.remove")}
      </Button>
    </div>
  );
}
