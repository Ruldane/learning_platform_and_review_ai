import { webUrl } from "@/shared/session-ui";
import { lessonPdfUrl, resourceFileUrl } from "./api";
import type { LessonOut, LessonView, ResourceOut, ResourceView } from "./types";

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
    // The shared address filter (http and https only), the address kept as is.
    url: webUrl(resource.url) ? resource.url : null,
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
