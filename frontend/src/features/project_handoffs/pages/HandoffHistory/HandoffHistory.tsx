import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { HandoffSummary } from "../../api";

export function HandoffHistory({ guides, currentId }: {
  guides: HandoffSummary[];
  currentId: string;
}) {
  return (
    <section className="grid gap-2">
      <h2 className="text-lg font-semibold">{t("projectHandoffs.history")}</h2>
      {!guides.length && <p className="text-muted-foreground">{t("projectHandoffs.empty")}</p>}
      <ul className="space-y-1">
        {guides.map((guide) => (
          <li key={guide.id}>
            <Link to={`?guide=${guide.id}`} className="underline"
              aria-current={guide.id === currentId ? "true" : undefined}>
              {guide.project_title} · <code>{guide.digest.slice(0, 12)}</code>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
