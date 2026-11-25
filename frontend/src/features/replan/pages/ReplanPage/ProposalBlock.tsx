import type { ReactNode } from "react";

/** A titled block of the proposal (summary, changes, load). */
export function ProposalBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-medium">{title}</h3>
      {children}
    </section>
  );
}
