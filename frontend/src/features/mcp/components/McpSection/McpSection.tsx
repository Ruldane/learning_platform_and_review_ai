import type { ReactNode, Ref } from "react";

interface McpSectionProps {
  title: string;
  intro?: string;
  /** Le titre prend le focus quand l'action qui vient de se faire a démonté le bouton cliqué. */
  headingRef?: Ref<HTMLHeadingElement>;
  children: ReactNode;
}

/** Un bloc titré de la page ; son titre peut recevoir le focus (`tabIndex={-1}`). */
export function McpSection({ title, intro, headingRef, children }: McpSectionProps) {
  return (
    <section className="flex flex-col gap-4">
      <header>
        <h2 ref={headingRef} tabIndex={-1} className="text-lg font-medium outline-none">
          {title}
        </h2>
        {intro ? <p className="mt-1 max-w-prose text-muted-foreground">{intro}</p> : null}
      </header>
      {children}
    </section>
  );
}
