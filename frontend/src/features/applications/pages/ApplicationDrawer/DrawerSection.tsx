import { useId, type ReactNode } from "react";

interface DrawerSectionProps {
  title: string;
  children: ReactNode;
}

/** Un bloc du tiroir : un titre de niveau 3 et son contenu. */
export function DrawerSection({ title, children }: DrawerSectionProps) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3 border-t pt-4">
      <h3 id={id} className="text-base font-semibold">
        {title}
      </h3>
      {children}
    </section>
  );
}
