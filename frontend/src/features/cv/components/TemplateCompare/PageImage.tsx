interface PageImageProps {
  src: string | undefined;
  alt: string;
  /** What is shown when this column has no page. */
  missing: string;
}

/** A page as an image, or the sentence saying it is missing on this side. */
export function PageImage({ src, alt, missing }: PageImageProps) {
  if (src === undefined) return <p className="text-sm text-muted-foreground">{missing}</p>;
  return <img src={src} alt={alt} className="w-full rounded-lg border bg-white" />;
}
