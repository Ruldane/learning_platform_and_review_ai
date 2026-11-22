import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { DebateSummary } from "../../api";
import { debatePath } from "../../hooks/useDebates";

export function DebateHistory({ debates }: { debates: DebateSummary[] }) {
  return (
    <section aria-labelledby="debate-history" className="flex flex-col gap-2">
      <h2 id="debate-history" className="text-xl font-semibold">
        {t("expertDebates.recent")}
      </h2>
      {debates.length > 0 ? (
        <ul className="divide-y divide-border">
          {debates.map((debate) => (
            <li key={debate.id} className="py-2">
              <Link className="break-words underline underline-offset-2" to={debatePath(debate.id)}>
                {debate.question}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p>{t("expertDebates.empty")}</p>
      )}
    </section>
  );
}
