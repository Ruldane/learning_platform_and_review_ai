import { t } from "@/shared/i18n/t";

interface OverlayPageProps {
  n: number;
  original: string | undefined;
  render: string | undefined;
  /** Où le curseur coupe la page, de 0 à 100 : l'original à gauche, le modèle recréé à droite. */
  position: number;
}

/** Une page de l'original et celle du modèle recréé superposées, coupées au curseur. */
export function OverlayPage({ n, original, render, position }: OverlayPageProps) {
  const both = original !== undefined && render !== undefined;
  return (
    <section aria-label={t("cv.template.page", { n })} className="relative">
      {original ? (
        <img
          src={original}
          alt={t("cv.template.originalAlt", { n })}
          className="block w-full rounded-lg border bg-white"
        />
      ) : null}
      {render ? (
        <img
          src={render}
          alt={t("cv.template.renderAlt", { n })}
          className={
            both
              ? "absolute inset-0 h-full w-full rounded-lg border bg-white"
              : "block w-full rounded-lg border bg-white"
          }
          style={both ? { clipPath: `inset(0 0 0 ${position}%)` } : undefined}
        />
      ) : null}
      {both ? (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 w-0.5 bg-primary"
          style={{ left: `${position}%` }}
        />
      ) : null}
    </section>
  );
}
