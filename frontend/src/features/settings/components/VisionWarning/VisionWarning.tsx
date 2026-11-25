import { TriangleAlert } from "lucide-react";
import { t } from "@/shared/i18n/t";

/** Warns that CV design capture is disabled (vision level without a vision model). */
export function VisionWarning({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <p
      role="note"
      className="flex items-start gap-2 rounded-lg border border-amber-700/40 bg-amber-50 px-3 py-2 text-sm text-amber-900"
    >
      <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span>{t("settings.vision.warning")}</span>
    </p>
  );
}
