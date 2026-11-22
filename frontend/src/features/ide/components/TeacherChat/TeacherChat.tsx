import { useId, type ReactNode, type Ref } from "react";
import { t } from "@/shared/i18n/t";
import { ChatComposer } from "@/shared/ui/ChatComposer";
import { ChatThread } from "@/shared/ui/ChatThread";
import { ChatFooter } from "../ChatFooter";
import { ChatMessage } from "../ChatMessage";
import type { ChatItem } from "../chatItems";
import { PendingMessage } from "./PendingMessage";
import { QuickActions } from "./QuickActions";

interface TeacherChatProps {
  items: ChatItem[];
  /** Le professeur écrit : le fil le dit, « Envoyer » attend. */
  typing: boolean;
  busy: boolean;
  /** Ce qu'il faut dire sous le fil : pourquoi rien n'est parti, ou l'erreur. */
  notice: { tone: "status" | "error"; text: string } | null;
  canExplain: boolean;
  launchMenu?: ReactNode;
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

function renderMessage(
  item: ChatItem,
  busy: boolean,
  onAccept: TeacherChatProps["onAccept"],
  onReject: TeacherChatProps["onReject"],
) {
  if (item.type === "pending") return <PendingMessage key={item.id} text={item.text} />;
  return (
    <ChatMessage
      key={item.id}
      note={item.note}
      mine={item.mine}
      tag={item.tag}
      busy={busy}
      onAccept={() => onAccept(item.id)}
      onReject={() => onReject(item.id)}
    />
  );
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
  launchMenu,
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
        label={t("ide.chat.thread")}
        emptyText={t("ide.teacher.empty")}
        footer={<ChatFooter typing={typing} notice={notice} />}
        scrollSignal={`${typing}|${notice?.text ?? ""}`}
      >
        {items.map((item) => renderMessage(item, proposalsBusy, onAccept, onReject))}
      </ChatThread>
      {launchMenu ? <div className="px-3 py-2">{launchMenu}</div> : null}
      <ChatComposer
        busy={busy}
        label={t("ide.teacher.question")}
        placeholder={t("ide.chat.placeholder")}
        onSend={onSend}
        actions={<QuickActions busy={busy} canExplain={canExplain} onHint={onHint} onWhy={onWhy} />}
      />
    </section>
  );
}
