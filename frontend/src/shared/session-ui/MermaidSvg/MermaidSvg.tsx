import { useEffect, useId, useState } from "react";
import { t } from "@/shared/i18n/t";

interface MermaidSvgProps {
  code: string;
  title: string;
}

type Rendered = { code: string; svg: string } | { code: string; failed: true };

/**
 * Schéma Mermaid en SVG, en niveau de sécurité `strict` (balises encodées, `click` coupé : SPEC
 * 17.2). Sert de repli au tableau Excalidraw et de rendu des schémas des leçons. Mermaid ne se
 * charge qu'au premier schéma affiché. Erreur : le code s'affiche dans un bloc `<pre>`.
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
        // Mermaid laisse un élément de travail dans le document quand le rendu échoue.
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
      // Le SVG vient de Mermaid en `securityLevel: "strict"`, qui l'assainit.
      dangerouslySetInnerHTML={{ __html: current.svg }}
    />
  );
}
