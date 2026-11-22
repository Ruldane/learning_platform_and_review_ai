/** La question qui part reste atténuée à droite jusqu'à ce que le serveur la rende. */
export function PendingMessage({ text }: { text: string }) {
  return (
    <li className="flex justify-end">
      <p className="max-w-[90%] rounded-2xl bg-accent px-3 py-2 text-sm whitespace-pre-wrap text-accent-foreground opacity-70">
        {text}
      </p>
    </li>
  );
}
