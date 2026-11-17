import type { ReactNode } from "react";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";

interface PublicPageProps {
  title: string;
  settled?: boolean;
  children: ReactNode;
}

/**
 * Le cadre d'une page publique (connexion, reprise), hors de la mise en page : sans barre ni
 * navigation, `<main>` et un titre qui prend le focus à l'ouverture. On y arrive souvent par une
 * redirection (porte, déconnexion) qui a démonté la page où se trouvait le focus : sans cela, la
 * personne au clavier repartirait du haut du document. `settled` vaut faux tant que la page montre
 * un état d'erreur avec son bouton « Réessayer » : le titre reprend le focus quand l'erreur
 * disparaît (le bouton cliqué est alors démonté), jamais avant.
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
