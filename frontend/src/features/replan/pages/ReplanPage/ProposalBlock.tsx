import type { ReactNode } from "react";

/** Un bloc titré de la proposition (bilan, changements, charge). */
export function ProposalBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-medium">{title}</h3>
      {children}
    </section>
  );
}
