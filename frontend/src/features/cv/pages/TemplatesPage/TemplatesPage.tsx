import { Link, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { POLL_MS } from "../../hooks/useProfile";
import { useTemplates } from "../../hooks/useTemplates";
import { FILE_FIELD_ID } from "./PdfFields";
import { TemplateCreateForm } from "./TemplateCreateForm";
import { TemplateList } from "./TemplateList";

const link = "text-sm font-medium underline underline-offset-4";

const focusFileField = () => document.getElementById(FILE_FIELD_ID)?.focus();

/**
 * Les modèles de CV (`/carriere/cv`) : la liste, puis l'envoi d'un PDF (ou d'un PDF déjà importé)
 * pour en créer un. Une création mène à la page du modèle, où le Maquettiste travaille en direct.
 */
export function TemplatesPage({ pollMs = POLL_MS }: { pollMs?: number }) {
  const navigate = useNavigate();
  const query = useTemplates(pollMs);
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t("cv.templatesPage.title")}</h1>
        <p className="max-w-prose text-muted-foreground">{t("cv.templatesPage.intro")}</p>
        <nav className="flex flex-wrap gap-4">
          <Link to="/carriere/profil" className={link}>
            {t("cv.templatesPage.profileLink")}
          </Link>
          <Link to="/carriere/cv/versions" className={link}>
            {t("cv.templatesPage.versionsLink")}
          </Link>
          <Link to="/carriere/offres" className={link}>
            {t("cv.templatesPage.offersLink")}
          </Link>
        </nav>
      </header>
      {query.data === undefined ? (
        query.isError ? (
          <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
        ) : (
          <LoadingState label={t("cv.templatesPage.loading")} />
        )
      ) : query.data.length === 0 ? (
        <EmptyState
          title={t("cv.templatesPage.emptyTitle")}
          description={t("cv.templatesPage.emptyHint")}
          action={{ label: t("cv.templatesPage.emptyAction"), onClick: focusFileField }}
        />
      ) : (
        <TemplateList templates={query.data} />
      )}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">{t("cv.templatesPage.formTitle")}</h2>
        <TemplateCreateForm onCreated={(id) => void navigate(`/carriere/cv/modeles/${id}`)} />
      </section>
    </div>
  );
}
