import { useRef, useState, type ComponentType } from "react";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { LessonReader } from "../../components/LessonReader";
import type { useResourceStatus } from "../../hooks/useResourceStatus";
import { toLessonView, toResourceView } from "../../toView";
import type { LessonOut } from "../../types";
import { LessonConversationActions } from "./LessonConversationActions";
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
          <LessonConversationActions
            lessonId={lesson.id}
            professorButton={openButton}
            onAskProfessor={Panel ? () => setDiscussion({ passage: null }) : undefined}
          />
        }
      />
      <LessonResources resources={lesson.resources.map(toResourceView)} status={resources} />
      {Panel && discussion ? (
        <Panel lessonId={lesson.id} passage={discussion.passage} onClose={close} />
      ) : null}
    </>
  );
}
