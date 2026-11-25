import type { ReactNode, Ref } from "react";

interface McpSectionProps {
  title: string;
  intro?: string;
  /** The title takes focus when the action just taken unmounted the clicked button. */
  headingRef?: Ref<HTMLHeadingElement>;
  children: ReactNode;
}

/** A titled block of the page; its title can receive focus (`tabIndex={-1}`). */
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
