import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { POLL_MS } from "../../hooks/useProfile";
import { useTemplate } from "../../hooks/useTemplates";
import { cvKeys } from "../../queryKeys";
import { TemplateBody } from "./TemplateBody";

const LIST_PATH = "/career/cv";

interface TemplatePageProps {
  pollMs?: number;
  /** Only used by the tests (fake WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * A CV template (`/career/cv/templates/:templateId`): the Maquettiste's thread, the comparison with
 * the original CV, the replaced fonts and the « Valider / Ajuster » question.
 */
export function TemplatePage({ pollMs = POLL_MS, createSocket }: TemplatePageProps) {
  const { templateId = "" } = useParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const query = useTemplate(templateId, pollMs);
  const template = query.data;
  const reload = () => void client.invalidateQueries({ queryKey: cvKeys.template(templateId) });

  if (template === undefined) {
    if (query.error instanceof ApiError && query.error.status === 404) {
      return (
        <EmptyState
          title={t("cv.templatePage.notFoundTitle")}
          description={t("cv.templatePage.notFoundHint")}
          action={{ label: t("cv.templatePage.back"), onClick: () => void navigate(LIST_PATH) }}
        />
      );
    }
    if (query.isError) {
      return (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      );
    }
    return <LoadingState label={t("cv.templatePage.loading")} />;
  }
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <Link to={LIST_PATH} className="text-sm underline">
          {t("cv.templatePage.back")}
        </Link>
        <h1 className="text-2xl font-semibold">{template.name}</h1>
      </header>
      <TemplateBody template={template} onChange={reload} createSocket={createSocket} />
    </div>
  );
}
