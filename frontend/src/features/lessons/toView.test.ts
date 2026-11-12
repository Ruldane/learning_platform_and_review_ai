import { describe, expect, it } from "vitest";
import { lessonOut, resourceOut } from "@/test/lessonsApi";
import { lessonRefetchInterval } from "./hooks/useLesson";
import { toLessonView, toResourceView, webUrl } from "./toView";
import type { LessonOut, ResourceOut } from "./types";

const lesson = (over: Record<string, unknown> = {}) => lessonOut(over) as unknown as LessonOut;
const resource = (over: Record<string, unknown> = {}) =>
  resourceOut(over) as unknown as ResourceOut;

describe("webUrl", () => {
  it("keeps http and https addresses only", () => {
    expect(webUrl("https://docs.python.org/3/")).toBe("https://docs.python.org/3/");
    expect(webUrl("http://example.org")).toBe("http://example.org");
    expect(webUrl("javascript:alert(1)")).toBeNull();
    expect(webUrl("data:text/html,<b>x</b>")).toBeNull();
    expect(webUrl("/relative/path")).toBeNull();
    expect(webUrl("")).toBeNull();
  });
});

describe("toLessonView", () => {
  it("links the PDF only when it is ready", () => {
    expect(toLessonView(lesson()).pdfUrl).toMatch(/\/lessons\/l1\/pdf$/);
    expect(toLessonView(lesson({ pdf_available: false })).pdfUrl).toBeNull();
    expect(toLessonView(lesson())).toMatchObject({
      title: "Les variables et les types",
      wordCount: 1400,
    });
  });
});

describe("toResourceView", () => {
  it("renames the fields and builds the local copy address", () => {
    expect(toResourceView(resource({ has_local_copy: true }))).toMatchObject({
      id: "r1",
      url: "https://docs.python.org/3/tutorial/",
      durationMinutes: 45,
      localCopyUrl: expect.stringMatching(/\/resources\/r1\/file$/),
      status: "to_read",
    });
    expect(toResourceView(resource()).localCopyUrl).toBeNull();
  });

  it("drops an address that is not a web page", () => {
    expect(toResourceView(resource({ url: "javascript:alert(1)" })).url).toBeNull();
  });
});

describe("lessonRefetchInterval", () => {
  it("polls an unfinished lesson, quickly while it is written, and stops once ready", () => {
    expect(lessonRefetchInterval("generating")).toBe(5000);
    expect(lessonRefetchInterval("pending")).toBe(15_000);
    expect(lessonRefetchInterval("failed")).toBe(15_000);
    expect(lessonRefetchInterval("ready")).toBe(false);
    expect(lessonRefetchInterval(undefined)).toBe(false);
  });
});
