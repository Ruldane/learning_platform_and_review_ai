import { t } from "@/shared/i18n/t";
import type { UserCommand } from "@/shared/realtime/types";

interface UserMessageBubbleProps {
  text: string;
  /** Commande du débat (« Plus court »…) ; `null` ou absente : un message libre. */
  command?: UserCommand;
}

/** Message de l'utilisateur dans le fil, aligné à droite et étiqueté « Toi ». */
export function UserMessageBubble({ text, command = null }: UserMessageBubbleProps) {
  return (
    <article className="ml-auto max-w-[85%] rounded-xl bg-accent px-3 py-2 text-accent-foreground motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200">
      <p className="text-xs font-medium">{t("session.bubble.you")}</p>
      {command ? (
        <p className="font-medium">
          {t("session.bubble.command", { command: t(`session.commands.${command}`) })}
        </p>
      ) : null}
      {text === "" ? null : <p className="whitespace-pre-wrap break-words">{text}</p>}
    </article>
  );
}
