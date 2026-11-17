import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";

interface ExportCardProps {
  /** L'adresse de l'archive : un lien plein, le navigateur télécharge le zip. */
  href: string;
}

/**
 * « Exporter toutes mes données » : ce que contient l'archive (jamais les clés d'API) et le lien.
 */
export function ExportCard({ href }: ExportCardProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col items-start gap-3 rounded-xl border border-border bg-card p-4"
    >
      <h2 id={titleId} className="text-lg font-semibold">
        {t("account.export.title")}
      </h2>
      <p className="text-sm text-muted-foreground">{t("account.export.description")}</p>
      <a href={href} className={buttonVariants({ variant: "default" })}>
        {t("account.export.link")}
      </a>
    </section>
  );
}
