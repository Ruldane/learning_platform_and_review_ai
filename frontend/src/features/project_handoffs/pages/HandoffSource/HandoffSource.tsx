import { Link } from "react-router";
import type { components } from "@/shared/api/schema";
import { t } from "@/shared/i18n/t";

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" });

type Source = components["schemas"]["ProjectHandoffSource"];

export function HandoffSource({ source }: { source: Source }) {
  return (
    <section className="grid gap-2 rounded border p-4">
      <h2 className="text-lg font-semibold">{t("projectHandoffs.submission")}</h2>
      <p className="font-medium">{source.project_title}</p>
      <p className="text-sm text-muted-foreground">
        {t("projectHandoffs.submittedAt")}{" "}
        <time dateTime={source.submitted_at}>{dateFormat.format(new Date(source.submitted_at))}</time>
      </p>
      {source.description && <p className="whitespace-pre-wrap">{source.description}</p>}
      {source.repo_url && (
        <p className="break-all">{t("projectHandoffs.repository")} <code>{source.repo_url}</code></p>
      )}
      <Link to={`/skills/portfolio/${source.project_id}`} className="w-fit underline">
        {t("projectHandoffs.openProject")}
      </Link>
    </section>
  );
}
