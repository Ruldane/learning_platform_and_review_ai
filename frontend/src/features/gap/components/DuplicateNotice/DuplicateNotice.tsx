import { t } from "@/shared/i18n/t";
import type { DuplicateView } from "../viewTypes";
import { DuplicateItem } from "./DuplicateItem";

interface DuplicateNoticeProps {
  duplicates: DuplicateView[];
  onOpen: (postingId: string) => void;
  onDistinct: (postingId: string) => void;
}

/**
 * Les offres déjà connues qui ressemblent à celle qu'on vient d'ajouter. « Certain » : le jour de
 * l'ajout ; « probable » : on propose d'ouvrir l'ancienne ou de dire que ce sont deux offres ;
 * « possible » : une simple mention.
 */
export function DuplicateNotice({ duplicates, onOpen, onDistinct }: DuplicateNoticeProps) {
  if (duplicates.length === 0) return null;
  return (
    <ul aria-label={t("gap.duplicate.label")} className="flex flex-col gap-2">
      {duplicates.map((duplicate) => (
        <DuplicateItem
          key={duplicate.postingId}
          duplicate={duplicate}
          onOpen={onOpen}
          onDistinct={onDistinct}
        />
      ))}
    </ul>
  );
}
