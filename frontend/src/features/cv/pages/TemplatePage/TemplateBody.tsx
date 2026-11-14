import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { InlineError } from "@/shared/ui/states/InlineError";
import { FontGapNotice } from "../../components/FontGapNotice";
import { TemplateCompare } from "../../components/TemplateCompare";
import { toZoneViews } from "../../toView";
import type { TemplateOut } from "../../types";
import { pageRange, templatePageUrl } from "../../urls";
import { ReadyActions } from "./ReadyActions";
import { TemplateRun } from "./TemplateRun";

interface TemplateBodyProps {
  template: TemplateOut;
  onChange: () => void;
  createSocket?: SocketFactory;
}

/** Ce que le modèle dit de lui-même : l'état en une phrase. */
const statusKey = (status: TemplateOut["status"]) => {
  if (status === "capturing") return "cv.templatePage.capturing";
  if (status === "review") return "cv.templatePage.review";
  if (status === "failed") return "cv.templatePage.failed";
  return "cv.templatePage.ready";
};

/** Les pages du CV d'origine et, dès la première passe, celles du rendu courant. */
function comparePages(template: TemplateOut) {
  const url = (kind: "original" | "render", pass: number) => (n: number) =>
    templatePageUrl(template.id, kind, n, pass);
  return {
    original: pageRange(template.page_count, url("original", 0)),
    render:
      template.passes > 0 ? pageRange(template.page_count, url("render", template.passes)) : [],
  };
}

/**
 * Le modèle : le fil du Maquettiste, la comparaison avec le CV d'origine (mise à jour à chaque
 * passe), les polices remplacées, et, quand il est prêt, de quoi l'utiliser.
 */
export function TemplateBody({ template, onChange, createSocket }: TemplateBodyProps) {
  const pages = comparePages(template);
  return (
    <div className="flex flex-col gap-6">
      <p role="status" className="font-medium">
        {t(statusKey(template.status))}
      </p>
      {template.status === "failed" ? (
        <InlineError message={template.failure_reason ?? t("cv.templatePage.failedFallback")} />
      ) : null}
      {!template.selectable ? (
        <p className="text-sm text-muted-foreground">{t("cv.templatePage.notSelectable")}</p>
      ) : null}
      {template.session_id ? (
        <TemplateRun
          sessionId={template.session_id}
          onChange={onChange}
          createSocket={createSocket}
        />
      ) : null}
      <TemplateCompare
        originalPages={pages.original}
        renderPages={pages.render}
        score={template.score}
        zones={toZoneViews(template.zones)}
        passes={template.passes}
      />
      <FontGapNotice gaps={template.font_gaps} />
      {template.status === "ready" ? <ReadyActions template={template} /> : null}
    </div>
  );
}
