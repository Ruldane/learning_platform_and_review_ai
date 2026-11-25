import { t } from "@/shared/i18n/t";
import type { DuplicateView } from "../viewTypes";
import { DuplicateItem } from "./DuplicateItem";

interface DuplicateNoticeProps {
  duplicates: DuplicateView[];
  onOpen: (postingId: string) => void;
  onDistinct: (postingId: string) => void;
}

/**
 * Known postings that resemble the one just added. « Certain »: same day as the
 * addition; « probable »: offer to open the old one or to say they are two postings;
 * « possible »: a plain mention.
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
