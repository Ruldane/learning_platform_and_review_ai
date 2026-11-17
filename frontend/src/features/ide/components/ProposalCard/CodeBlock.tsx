interface CodeBlockProps {
  label: string;
  text: string;
}

/** Un passage de code sous son titre (« Avant » ou « Après »). */
export function CodeBlock({ label, text }: CodeBlockProps) {
  return (
    <figure className="flex min-w-0 flex-col gap-1">
      <figcaption className="text-xs font-medium">{label}</figcaption>
      <pre className="overflow-x-auto rounded-lg bg-muted p-2 font-mono text-xs whitespace-pre">
        {text}
      </pre>
    </figure>
  );
}
