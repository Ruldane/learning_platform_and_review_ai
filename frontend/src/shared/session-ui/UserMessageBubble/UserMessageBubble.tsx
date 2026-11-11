import { t } from "@/shared/i18n/t";

interface UserMessageBubbleProps {
  text: string;
}

/** Message de l'utilisateur dans le fil, aligné à droite et étiqueté « Toi ». */
export function UserMessageBubble({ text }: UserMessageBubbleProps) {
  return (
    <article className="ml-auto max-w-[85%] rounded-xl bg-accent px-3 py-2 text-accent-foreground motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200">
      <p className="text-xs font-medium">{t("session.bubble.you")}</p>
      <p className="whitespace-pre-wrap break-words">{text}</p>
    </article>
  );
}
