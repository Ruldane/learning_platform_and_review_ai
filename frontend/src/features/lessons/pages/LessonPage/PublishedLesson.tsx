import { useRef, useState, type ComponentType } from "react";
import { t } from "@/shared/i18n/t";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { Button } from "@/shared/ui/button";
import { LessonReader } from "../../components/LessonReader";
import type { useResourceStatus } from "../../hooks/useResourceStatus";
import { toLessonView, toResourceView } from "../../toView";
import type { LessonOut } from "../../types";
import { LessonResources } from "./LessonResources";

export interface LessonConversationPanelProps {
  lessonId: string;
  passage: LessonPassage | null;
  onClose: () => void;
}

interface PublishedLessonProps {
  lesson: LessonOut;
  resources: ReturnType<typeof useResourceStatus>;
  conversationPanel?: ComponentType<LessonConversationPanelProps>;
}

export function PublishedLesson({
  lesson,
  resources,
  conversationPanel: Panel,
}: PublishedLessonProps) {
  const [discussion, setDiscussion] = useState<{ passage: LessonPassage | null } | null>(null);
  const openButton = useRef<HTMLButtonElement>(null);
  const close = () => {
    setDiscussion(null);
    // Le clic dans le panneau peut faire disparaître la sélection et son bouton.
    openButton.current?.focus({ preventScroll: true });
  };
  return (
    <>
      <LessonReader
        lesson={toLessonView(lesson)}
        onAskProfessor={Panel ? (passage) => setDiscussion({ passage }) : undefined}
        conversationButton={
          Panel ? (
            <Button
              type="button"
              ref={openButton}
              variant="outline"
              className="self-start"
              onClick={() => setDiscussion({ passage: null })}
            >
              {t("lessons.reader.openConversation")}
            </Button>
          ) : null
        }
      />
      <LessonResources resources={lesson.resources.map(toResourceView)} status={resources} />
      {Panel && discussion ? (
        <Panel lessonId={lesson.id} passage={discussion.passage} onClose={close} />
      ) : null}
    </>
  );
}
