import { describe, expect, it } from "vitest";
import type { LessonStatus } from "../types";
import {
  lessonRefetchInterval,
  lessonsRefetchInterval,
  MAX_IDLE_POLLS,
  MAX_PDF_POLLS,
} from "./polling";

const lesson = (status: LessonStatus, pdf_available = false) => ({ status, pdf_available });

describe("lessonRefetchInterval", () => {
  it("polls an unfinished lesson, quickly while it is written", () => {
    expect(lessonRefetchInterval(lesson("generating"), 0)).toBe(5000);
    expect(lessonRefetchInterval(lesson("pending"), 0)).toBe(15_000);
    expect(lessonRefetchInterval(lesson("failed"), 0)).toBe(15_000);
    expect(lessonRefetchInterval(undefined, 0)).toBe(false);
  });

  it("polls a ready lesson until its PDF arrives, for a bounded time", () => {
    expect(lessonRefetchInterval(lesson("ready", true), 0)).toBe(false);
    expect(lessonRefetchInterval(lesson("ready"), 0)).toBe(5000);
    expect(lessonRefetchInterval(lesson("ready"), MAX_PDF_POLLS - 1)).toBe(5000);
    expect(lessonRefetchInterval(lesson("ready"), MAX_PDF_POLLS)).toBe(false);
  });
});

describe("lessonsRefetchInterval", () => {
  const list = (...statuses: LessonStatus[]) => statuses.map((status) => ({ status }));

  it("polls quickly while a lesson is written", () => {
    expect(lessonsRefetchInterval(list("ready", "generating", "pending"), 99)).toBe(5000);
  });

  it("polls slowly while lessons wait, for a bounded time after the last writing", () => {
    expect(lessonsRefetchInterval(list("ready", "pending"), 0)).toBe(15_000);
    expect(lessonsRefetchInterval(list("failed"), 0)).toBe(15_000);
    expect(lessonsRefetchInterval(list("pending"), MAX_IDLE_POLLS)).toBe(false);
  });

  it("stops when every lesson is ready, or with nothing read yet", () => {
    expect(lessonsRefetchInterval(list("ready", "ready"), 0)).toBe(false);
    expect(lessonsRefetchInterval([], 0)).toBe(false);
    expect(lessonsRefetchInterval(undefined, 0)).toBe(false);
  });
});
