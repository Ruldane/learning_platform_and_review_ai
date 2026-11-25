import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { LessonPage } from "./pages/LessonPage";
import type { LessonUpdatesPanelProps } from "./pages/LessonPage/LessonPage";
import type { LessonConversationPanelProps } from "./pages/LessonPage/PublishedLesson";
import { LessonsPage } from "./pages/LessonsPage";
import { LibraryPage } from "./pages/LibraryPage";

/**
 * Learn, 4th and 5th entries: the program's lessons (one per module, to read or as PDF) and the
 * resource library (SPEC 3.5 and 3.6). The reader takes the width of the shell: its
 * reading column (72 characters) and its table of contents sit side by side.
 */
export function makeLessonsManifest(
  conversationPanel?: ComponentType<LessonConversationPanelProps>,
  updatesPanel?: ComponentType<LessonUpdatesPanelProps>,
): FeatureManifest {
  return {
    id: "lessons",
    routes: [
      { path: "learn/lessons", Component: LessonsPage },
      {
        path: "learn/lessons/:lessonId",
        element: createElement(LessonPage, { conversationPanel, updatesPanel }),
        handle: { wide: true },
      },
      { path: "learn/library", Component: LibraryPage },
    ],
    nav: [
      { section: "learn", labelKey: "lessons.nav.lessons", path: "/learn/lessons", order: 4 },
      {
        section: "learn",
        labelKey: "lessons.nav.library",
        path: "/learn/library",
        order: 5,
      },
    ],
  };
}
