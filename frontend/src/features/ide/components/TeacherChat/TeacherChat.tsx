import { useId, type Ref } from "react";
import { t } from "@/shared/i18n/t";
import { ChatComposer } from "../ChatComposer";
import { ChatFooter } from "../ChatFooter";
import { ChatThread } from "../ChatThread";
import type { ChatItem } from "../chatItems";

interface TeacherChatProps {
  items: ChatItem[];
  /** Le professeur écrit : le fil le dit, « Envoyer » attend. */
  typing: boolean;
  busy: boolean;
  /** Ce qu'il faut dire sous le fil : pourquoi rien n'est parti, ou l'erreur. */
  notice: { tone: "status" | "error"; text: string } | null;
  canExplain: boolean;
  /** Une décision sur une proposition est en cours. */
  proposalsBusy: boolean;
  onSend: (question: string) => Promise<boolean>;
  onHint: () => void;
  onWhy: () => void;
  onAccept: (noteId: string) => void;
  onReject: (noteId: string) => void;
  /** Reçoit le focus quand une proposition quitte la liste d'attente (accepter, refuser). */
  headingRef?: Ref<HTMLHeadingElement>;
}

/**
 * Le professeur en chat : un panneau de hauteur fixe (collé sous la barre du haut sur grand écran)
 * dont le fil défile à l'intérieur, la saisie en bas. Les notes déclenchées seules (erreur
 * d'exécution, indice, minuterie) s'insèrent dans le fil avec une petite étiquette.
 */
export function TeacherChat({
  items,
  typing,
  busy,
  notice,
  canExplain,
  proposalsBusy,
  onSend,
  onHint,
  onWhy,
  onAccept,
  onReject,
  headingRef,
}: TeacherChatProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex h-[min(42rem,calc(100dvh-6rem))] min-h-80 flex-col overflow-hidden rounded-xl border border-border bg-background xl:sticky xl:top-4"
    >
      <h2
        id={headingId}
        ref={headingRef}
        tabIndex={-1}
        className="border-b border-border px-3 py-2 font-medium outline-none"
      >
        {t("ide.teacher.title")}
      </h2>
      <ChatThread
        items={items}
        busy={proposalsBusy}
        onAccept={onAccept}
        onReject={onReject}
        footer={<ChatFooter typing={typing} notice={notice} />}
        footerKey={`${typing}|${notice?.text ?? ""}`}
      />
      <ChatComposer
        busy={busy}
        canExplain={canExplain}
        onSend={onSend}
        onHint={onHint}
        onWhy={onWhy}
      />
    </section>
  );
}
