import type { ReactNode } from "react";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";

/**
 * Le cadre d'une page publique (connexion, reprise), hors de la mise en page : sans barre ni
 * navigation, `<main>` et un titre qui prend le focus à l'ouverture. On y arrive souvent par une
 * redirection (porte, déconnexion) qui a démonté la page où se trouvait le focus : sans cela, la
 * personne au clavier repartirait du haut du document.
 */
export function PublicPage({ title, children }: { title: string; children: ReactNode }) {
  const heading = useFocusOnMount<HTMLHeadingElement>(true);
  return (
    <main className="mx-auto flex w-full max-w-xl flex-col gap-6 px-6 py-16">
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold focus:outline-none">
        {title}
      </h1>
      {children}
    </main>
  );
}
