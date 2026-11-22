import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ChatMarkdown } from "@/shared/ui/ChatMarkdown";
import { buttonVariants } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { openPaperLab } from "../../api";

export function PaperLabDetail({ labId }: { labId: string }) {
  const lab = useQuery({
    queryKey: ["paperLabs", labId],
    queryFn: ({ signal }) => openPaperLab(labId, signal),
    refetchInterval: ({ state }) => (state.data?.stage === "queued" ? 1200 : false),
  });
  if (lab.isPending) return <LoadingState />;
  if (lab.isError) {
    return <ErrorState message={errorMessage(lab.error)} onRetry={() => void lab.refetch()} />;
  }
  const data = lab.data;
  return (
    <>
      <Link to="/apprendre/articles" className="w-fit underline underline-offset-4">
        {t("paperLab.list")}
      </Link>
      {data.title ? <h2 className="text-lg font-semibold">{data.title}</h2> : null}
      <a
        href={data.url}
        target="_blank"
        rel="noopener noreferrer"
        className="w-fit underline underline-offset-4"
      >
        {data.source_title ?? t("paperLab.source")}
      </a>
      {data.stage === "queued" ? <p role="status">{t("paperLab.preparing")}</p> : null}
      {data.stage === "failed" ? <p role="alert">{t("paperLab.failed")}</p> : null}
      {data.course ? <ChatMarkdown>{data.course}</ChatMarkdown> : null}
      {data.expected ? (
        <section className="rounded-lg border bg-muted/40 p-4">
          <h3 className="font-semibold">{t("paperLab.expected")}</h3>
          <p>{data.expected}</p>
        </section>
      ) : null}
      {data.ide_session_id ? (
        <Link
          to={"/code/" + encodeURIComponent(data.ide_session_id)}
          className={buttonVariants({ variant: "outline", className: "w-fit" })}
        >
          {t("paperLab.notebook")}
        </Link>
      ) : null}
    </>
  );
}
