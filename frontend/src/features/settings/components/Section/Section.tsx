import type { ReactNode } from "react";

/** A titled block of a settings screen. */
export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-medium">{title}</h2>
      {children}
    </section>
  );
}
