interface PageImageProps {
  src: string | undefined;
  alt: string;
  /** Ce qu'on dit quand cette colonne n'a pas de page. */
  missing: string;
}

/** Une page en image, ou la phrase qui dit qu'elle manque de ce côté. */
export function PageImage({ src, alt, missing }: PageImageProps) {
  if (src === undefined) return <p className="text-sm text-muted-foreground">{missing}</p>;
  return <img src={src} alt={alt} className="w-full rounded-lg border bg-white" />;
}
