import { t } from "@/shared/i18n/t";

interface DroppedBannerProps {
  /** The texts of the removed lines: a figure that no document confirms. */
  dropped: string[];
}

/** Banner for lines removed from the profile: their count, and their list on request. */
export function DroppedBanner({ dropped }: DroppedBannerProps) {
  if (dropped.length === 0) return null;
  const many = dropped.length > 1;
  return (
    <div role="status" className="rounded-xl border border-border bg-muted px-4 py-3 text-sm">
      <p className="font-medium">
        {many
          ? t("cv.profile.dropped.many", { count: dropped.length })
          : t("cv.profile.dropped.one")}
      </p>
      <details className="mt-1">
        <summary className="cursor-pointer text-muted-foreground">
          {many ? t("cv.profile.dropped.showMany") : t("cv.profile.dropped.showOne")}
        </summary>
        <ul className="mt-1 list-disc pl-5">
          {dropped.map((text, index) => (
            <li key={index}>{text}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
