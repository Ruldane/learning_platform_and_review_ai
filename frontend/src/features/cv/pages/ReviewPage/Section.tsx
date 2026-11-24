import type { ReactNode } from "react";

interface SectionProps {
  title: string;
  /** Section anchor. The heading can receive focus when following it. */
  id?: string;
  children: ReactNode;
}

/** Une partie de la page de revue : un titre et son contenu. */
export function Section({ title, id, children }: SectionProps) {
  return (
    <section id={id} aria-label={title} className="flex flex-col gap-3">
      <h2
        id={id ? `${id}-title` : undefined}
        tabIndex={id ? -1 : undefined}
        className="text-lg font-medium"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
