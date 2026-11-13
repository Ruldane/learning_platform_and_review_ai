import { useMemo, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SessionEvent } from "@/shared/realtime/types";
import { Board } from "@/shared/session-ui";
import { boardStatesFromEvents } from "../../boardStates";

/** Colonne de droite : les tableaux que le Tuteur dessine, en lecture seule. */
export function SessionBoard({ events }: { events: SessionEvent[] }) {
  const states = useMemo(() => boardStatesFromEvents(events), [events]);
  const [activeId, setActiveId] = useState<string | null>(null);
  return (
    <section aria-label={t("study.session.board")} className="min-w-0">
      <Board
        states={states}
        activeId={activeId}
        onSelect={setActiveId}
        onSendEdit={() => undefined}
        sending={false}
        readOnly
        labels={{
          label: t("study.session.board"),
          empty: t("study.session.boardEmpty"),
          drawing: t("study.session.boardDrawing"),
        }}
      />
    </section>
  );
}
