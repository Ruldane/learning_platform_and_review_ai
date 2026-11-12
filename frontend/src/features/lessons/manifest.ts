import type { FeatureManifest } from "@/shared/lib/feature";
import { LessonPage } from "./pages/LessonPage";
import { LessonsPage } from "./pages/LessonsPage";
import { LibraryPage } from "./pages/LibraryPage";

/**
 * Apprendre, 4e et 5e entrées : les leçons du programme (une par module, à lire ou en PDF) et la
 * bibliothèque de ressources (SPEC 3.5 et 3.6). Le lecteur occupe la largeur de la coquille : sa
 * colonne de lecture (72 caractères) et son sommaire tiennent côte à côte.
 */
export const lessonsManifest: FeatureManifest = {
  id: "lessons",
  routes: [
    { path: "apprendre/lecons", Component: LessonsPage },
    { path: "apprendre/lecons/:lessonId", Component: LessonPage, handle: { wide: true } },
    { path: "apprendre/bibliotheque", Component: LibraryPage },
  ],
  nav: [
    { section: "learn", labelKey: "lessons.nav.lessons", path: "/apprendre/lecons", order: 4 },
    {
      section: "learn",
      labelKey: "lessons.nav.library",
      path: "/apprendre/bibliotheque",
      order: 5,
    },
  ],
};
