import type { ReactNode } from "react";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";

interface PublicPageProps {
  title: string;
  settled?: boolean;
  children: ReactNode;
}

/**
 * The frame of a public page (login, resume), outside the layout: without bar or
 * navigation, a `<main>` and a heading that takes focus on opening. It is often reached through a
 * redirect (gate, sign-out) that unmounted the page holding focus: without it, the
 * keyboard user would restart from the top of the document. `settled` is false while the page shows
 * an error state with its « Réessayer » button: the heading takes focus when the error
 * disappears (the clicked button is then unmounted), never before.
 */
export function PublicPage({ title, settled = true, children }: PublicPageProps) {
  const heading = useFocusOnMount<HTMLHeadingElement>(settled);
  return (
    <main className="mx-auto flex w-full max-w-xl flex-col gap-6 px-6 py-16">
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold focus:outline-none">
        {title}
      </h1>
      {children}
    </main>
  );
}
