import ReactMarkdown, { type Components } from "react-markdown";

const HTTP_URL = /^https?:\/\//i;

/** Seules les adresses http(s) passent : jamais `javascript:` ni `data:`. */
const httpUrlOnly = (url: string) => (HTTP_URL.test(url) ? url : "");

const COMPONENTS: Components = {
  p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5">{children}</ol>,
  a: ({ href, children }) =>
    href ? (
      <a href={href} target="_blank" rel="noopener noreferrer" className="underline">
        {children}
      </a>
    ) : (
      <span>{children}</span>
    ),
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-md bg-muted p-2 text-xs text-foreground">
      {children}
    </pre>
  ),
  code: ({ children }) => (
    <code className="rounded bg-muted px-1 font-mono text-xs">{children}</code>
  ),
};

/**
 * Les réponses en Markdown sûr : paragraphes, listes, `code` en ligne, blocs de code. Le
 * contenu n'est pas fiable (SPEC 17.2) : le HTML brut est retiré (`skipHtml`), seules les adresses
 * http(s) passent, aucune image n'est chargée.
 */
export function ChatMarkdown({
  children,
  allowLinks = true,
}: {
  children: string;
  allowLinks?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 text-sm [&_pre_code]:bg-transparent [&_pre_code]:p-0">
      <ReactMarkdown
        skipHtml
        urlTransform={allowLinks ? httpUrlOnly : () => ""}
        components={COMPONENTS}
        disallowedElements={["img"]}
        unwrapDisallowed
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
