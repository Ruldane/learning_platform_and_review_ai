import { t } from "@/shared/i18n/t";

interface DroppedBannerProps {
  /** Les textes des lignes retirées : un chiffre qu'aucun document ne confirme. */
  dropped: string[];
}

/** Bandeau des lignes retirées du profil : leur nombre, et leur liste à la demande. */
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
