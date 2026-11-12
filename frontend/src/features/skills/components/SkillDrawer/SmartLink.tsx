import type { ReactNode } from "react";
import { Link } from "react-router";

const EXTERNAL = /^https?:\/\//i;

/** Un chemin de l'application passe par le routeur ; une adresse web s'ouvre dans un nouvel onglet. */
export function SmartLink({ url, children }: { url: string; children: ReactNode }) {
  const className = "text-primary underline underline-offset-2";
  if (EXTERNAL.test(url)) {
    return (
      <a href={url} target="_blank" rel="noreferrer" className={className}>
        {children}
      </a>
    );
  }
  return (
    <Link to={url} className={className}>
      {children}
    </Link>
  );
}
