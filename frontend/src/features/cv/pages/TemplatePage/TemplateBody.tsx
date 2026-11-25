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

/** What the template says about itself: its state in one sentence. */
const statusKey = (status: TemplateOut["status"]) => {
  if (status === "capturing") return "cv.templatePage.capturing";
  if (status === "review") return "cv.templatePage.review";
  if (status === "failed") return "cv.templatePage.failed";
  return "cv.templatePage.ready";
};

/** The pages of the original CV and, from the first pass, those of the current rendering. */
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
 * The template: the Maquettiste's thread, the comparison with the original CV (updated at each
 * pass), the replaced fonts and, once it is ready, how to use it.
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
          ready={template.status === "ready"}
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
