import { lessonPdfUrl, resourceFileUrl } from "./api";
import type { LessonOut, LessonView, ResourceOut, ResourceView } from "./types";

/** Une adresse web que le navigateur peut ouvrir sans risque : `http` ou `https`, rien d'autre. */
export function webUrl(url: string): string | null {
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

export function toLessonView(lesson: LessonOut): LessonView {
  return {
    title: lesson.title,
    markdown: lesson.markdown,
    wordCount: lesson.word_count,
    pdfUrl: lesson.pdf_available ? lessonPdfUrl(lesson.id) : null,
  };
}

export function toResourceView(resource: ResourceOut): ResourceView {
  return {
    id: resource.id,
    title: resource.title,
    url: webUrl(resource.url),
    type: resource.type,
    lang: resource.lang,
    durationMinutes: resource.duration_minutes,
    level: resource.level,
    author: resource.author,
    date: resource.date,
    reason: resource.reason,
    note: resource.note,
    localCopyUrl: resource.has_local_copy ? resourceFileUrl(resource.id) : null,
    status: resource.status,
  };
}
