import { t } from "@/shared/i18n/t";
import type { RequestView } from "../viewTypes";

/**
 * What the request would do, in full: method, route, target and each field with its value. All
 * is text (React escapes it): content from the web or from Claude never becomes markup.
 * A field whose value is not shown says so.
 */
export function RequestBlock({ request }: { request: RequestView }) {
  const { method, route, targetLabel, fields, truncated } = request;
  return (
    <div
      role="group"
      aria-label={t("mcp.confirmations.request.title")}
      className="flex flex-col gap-1 rounded-lg border border-border bg-background p-2 text-sm"
    >
      <p className="font-medium">{`${method} ${route}`}</p>
      {targetLabel ? (
        <p className="whitespace-pre-wrap break-words">
          {t("mcp.confirmations.request.target", { label: targetLabel })}
        </p>
      ) : null}
      {fields.length > 0 ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
          {fields.map((field, index) => (
            <div key={`${field.name}-${index}`} className="contents">
              <dt className="font-medium">{field.name}</dt>
              <dd className="whitespace-pre-wrap break-words">
                {field.value ?? (
                  <span className="text-muted-foreground">
                    {t("mcp.confirmations.request.notShown")}
                  </span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      {truncated ? (
        <p className="text-muted-foreground">{t("mcp.confirmations.request.cut")}</p>
      ) : null}
    </div>
  );
}
