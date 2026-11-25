import { t } from "@/shared/i18n/t";
import type { AtsCheckIdView } from "../viewTypes";

const KNOWN: AtsCheckIdView[] = [
  "selectable_text",
  "reading_order",
  "standard_headings",
  "contact_in_body",
  "font_sizes",
];

/** The name of a check; an unknown check keeps its identifier. */
export function checkName(id: string): string {
  return KNOWN.includes(id as AtsCheckIdView) ? t(`cv.ats.check.${id as AtsCheckIdView}`) : id;
}
