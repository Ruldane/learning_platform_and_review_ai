import { Link, useNavigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ProgramPicker } from "../../components/ProgramPicker";
import { usePrograms } from "../../useBook";
import { Edition } from "./Edition";

const BOOK_PATH = "/apprendre/livre";

export function BookPage({ pollMs = 3_000 }: { pollMs?: number }) {
  const { programId } = useParams();
  const navigate = useNavigate();
  const programs = usePrograms();
  const chosen = programs.data?.find((program) => program.id === programId)?.id;
  return (
    <div className="flex max-w-xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("book.title")}</h1>
      {programs.isPending ? <LoadingState /> : null}
      {programs.isError ? (
        <ErrorState
          message={errorMessage(programs.error)}
          onRetry={() => void programs.refetch()}
        />
      ) : null}
      {programs.data?.length === 0 ? (
        <Link to="/apprendre/objectifs" className="underline underline-offset-4">
          {t("book.program.empty")}
        </Link>
      ) : null}
      {programs.data?.length ? (
        <ProgramPicker
          active={chosen ?? ""}
          programs={programs.data}
          onPick={(id) => void navigate(id ? `${BOOK_PATH}/${encodeURIComponent(id)}` : BOOK_PATH)}
        />
      ) : null}
      {chosen ? (
        <>
          <Edition key={chosen} programId={chosen} pollMs={pollMs} />
          <details>
            <summary className="cursor-pointer font-medium">{t("book.notes.title")}</summary>
            <p className="mt-2 text-sm text-muted-foreground">{t("book.notes.help")}</p>
            <code>{t("book.notes.link")}</code>
          </details>
        </>
      ) : null}
    </div>
  );
}
