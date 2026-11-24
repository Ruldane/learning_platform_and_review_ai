import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { listDossiers } from "../../api";

export function DossierList() {
  const query = useQuery({
    queryKey: ["contributions", "list"],
    queryFn: ({ signal }) => listDossiers(signal),
  });
  if (query.isPending) return <LoadingState />;
  if (!query.data) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  if (!query.data.length) return null;
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">{t("contributions.dossiers")}</h2>
      <ul className="flex flex-col gap-2">
        {query.data.map((item) => (
          <li key={item.id} className="flex flex-wrap items-baseline justify-between gap-2">
            <Link
              to={`/skills/contributions/${encodeURIComponent(item.id)}`}
              className="underline underline-offset-4"
            >
              {item.issue.title}
            </Link>
            <span className="text-sm text-muted-foreground">
              {t(`contributions.status.${item.status}`)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
