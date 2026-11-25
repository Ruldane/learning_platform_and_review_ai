import { t } from "@/shared/i18n/t";

interface OverlayPageProps {
  n: number;
  original: string | undefined;
  render: string | undefined;
  /** Slider position, 0 to 100: the original on the left, the recreated template on the right. */
  position: number;
}

/** A page of the original and of the recreated template, overlaid and cut at the slider. */
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
