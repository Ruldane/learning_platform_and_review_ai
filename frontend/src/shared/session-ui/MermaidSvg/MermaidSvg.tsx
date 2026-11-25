import { useEffect, useId, useState } from "react";
import { t } from "@/shared/i18n/t";

interface MermaidSvgProps {
  code: string;
  title: string;
}

type Rendered = { code: string; svg: string } | { code: string; failed: true };

/**
 * Mermaid diagram as SVG, at the `strict` security level (encoded tags, `click` cut: SPEC
 * 17.2). Serves as the fallback for the Excalidraw board and renders lesson diagrams. Mermaid
 * loads only when the first diagram is shown. On error, the code is shown in a `<pre>` block.
 */
export function MermaidSvg({ code, title }: MermaidSvgProps) {
  const id = `mermaid-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const [rendered, setRendered] = useState<Rendered | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { default: mermaid } = await import("mermaid");
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
        const { svg } = await mermaid.render(id, code);
        if (!cancelled) setRendered({ code, svg });
      } catch {
        // Mermaid leaves a working element in the document when rendering fails.
        document.getElementById(`d${id}`)?.remove();
        if (!cancelled) setRendered({ code, failed: true });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, id]);

  const current = rendered?.code === code ? rendered : null;
  if (current && "failed" in current) {
    return (
      <div className="flex flex-col gap-2">
        <p role="alert" className="text-sm text-muted-foreground">
          {t("session.mermaid.failed")}
        </p>
        <pre className="overflow-x-auto rounded-lg border bg-muted p-3 text-xs">{code}</pre>
      </div>
    );
  }
  if (!current) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        {t("session.mermaid.rendering")}
      </p>
    );
  }
  return (
    <div
      role="img"
      aria-label={t("session.mermaid.label", { title })}
      className="overflow-x-auto [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      // The SVG comes from Mermaid with `securityLevel: "strict"`, which sanitizes it.
      dangerouslySetInnerHTML={{ __html: current.svg }}
    />
  );
}
