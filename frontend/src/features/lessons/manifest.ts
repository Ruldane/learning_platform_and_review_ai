import { createElement, type ComponentType } from "react";
import type { FeatureManifest } from "@/shared/lib/feature";
import { LessonPage } from "./pages/LessonPage";
import type { LessonUpdatesPanelProps } from "./pages/LessonPage/LessonPage";
import type { LessonConversationPanelProps } from "./pages/LessonPage/PublishedLesson";
import { LessonsPage } from "./pages/LessonsPage";
import { LibraryPage } from "./pages/LibraryPage";

/**
 * Apprendre, 4e et 5e entrées : les leçons du programme (une par module, à lire ou en PDF) et la
 * bibliothèque de ressources (SPEC 3.5 et 3.6). Le lecteur occupe la largeur de la coquille : sa
 * colonne de lecture (72 caractères) et son sommaire tiennent côte à côte.
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
