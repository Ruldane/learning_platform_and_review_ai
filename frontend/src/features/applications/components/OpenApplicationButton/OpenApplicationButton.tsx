import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";

interface OpenApplicationButtonProps {
  application: { id: string; company: string; title: string };
  onOpen: (id: string) => void;
  children: ReactNode;
}

/** Le bouton qui ouvre une fiche (carte et ligne du tableau) : son nom dit l'entreprise et le poste. */
export function OpenApplicationButton({
  application,
  onOpen,
  children,
}: OpenApplicationButtonProps) {
  const { id, company, title } = application;
  return (
    <button
      type="button"
      aria-label={t("applications.card.open", { company, title })}
      onClick={() => onOpen(id)}
      className="rounded text-left outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring"
    >
      {children}
    </button>
  );
}
