import { describe, expect, it } from "vitest";
import { lessonOut, resourceOut } from "@/test/lessonsApi";
import { toLessonView, toResourceView } from "./toView";
import type { LessonOut, ResourceOut } from "./types";

const lesson = (over: Record<string, unknown> = {}) => lessonOut(over) as unknown as LessonOut;
const resource = (over: Record<string, unknown> = {}) =>
  resourceOut(over) as unknown as ResourceOut;

describe("toResourceView : adresse", () => {
  it("keeps http and https addresses as given, nothing else", () => {
    const url = (address: string) => toResourceView(resource({ url: address })).url;
    expect(url("https://docs.python.org/3/")).toBe("https://docs.python.org/3/");
    expect(url("http://example.org")).toBe("http://example.org");
    expect(url("javascript:alert(1)")).toBeNull();
    expect(url("data:text/html,<b>x</b>")).toBeNull();
    expect(url("/relative/path")).toBeNull();
    expect(url("")).toBeNull();
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
