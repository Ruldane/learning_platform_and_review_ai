import { describe, expect, it } from "vitest";
import { noteOut, sessionSummary, exerciseOut } from "@/test/ideApi";
import type { Exercise, Note, SessionSummary } from "./types";
import {
  excerpt,
  isFailedRun,
  toAnnotations,
  toExerciseViews,
  toFreeSessions,
  toNoteViews,
} from "./toView";

const note = (over: Record<string, unknown>) => noteOut(over) as unknown as Note;

describe("excerpt", () => {
  it("cuts lines from 1 and refuses a range outside the file", () => {
    expect(excerpt("a\nb\nc", 2, 3)).toBe("b\nc");
    expect(excerpt("a\nb", 1, 3)).toBeNull();
    expect(excerpt("a\nb", 0, 1)).toBeNull();
    expect(excerpt(undefined, 1, 1)).toBeNull();
  });
});

describe("toNoteViews", () => {
  it("names Claude on a note written through the MCP, with the token label when it differs", () => {
    const views = toNoteViews(
      [
        note({ id: "a", author: "claude", author_label: null, origin: "mcp" }),
        note({ id: "b", author: "claude", author_label: "Claude Code", origin: "mcp" }),
        note({ id: "c", author: "claude", author_label: "Mon jeton", origin: "mcp" }),
        note({ id: "d", author: "professor", author_label: null, origin: "app" }),
      ],
      {},
    );
    expect(views.map((v) => [v.authorLabel, v.origin])).toEqual([
      ["Claude", "mcp"],
      ["Claude Code", "mcp"],
      ["Claude (Mon jeton)", "mcp"],
      ["Le professeur", "app"],
    ]);
  });

  it("numbers the hints in the order they were written", () => {
    const views = toNoteViews(
      [
        note({ id: "b", created_at: "2026-11-17T10:07:00Z" }),
        note({ id: "x", kind: "explanation", created_at: "2026-11-17T10:06:00Z" }),
        note({ id: "a", created_at: "2026-11-17T10:05:00Z" }),
      ],
      {},
    );
    expect(views.map((view) => [view.id, view.hintLevel])).toEqual([
      ["a", 1],
      ["x", null],
      ["b", 2],
    ]);
  });

  it("shows the real level of a hint when the teacher gave one", () => {
    const views = toNoteViews(
      [
        note({ id: "a", level: 3, created_at: "2026-11-17T10:05:00Z" }),
        note({ id: "b", level: 1, created_at: "2026-11-17T10:06:00Z" }),
        note({ id: "c", kind: "explanation", level: 2, created_at: "2026-11-17T10:07:00Z" }),
      ],
      {},
    );
    expect(views.map((view) => [view.id, view.hintLevel])).toEqual([
      ["a", 3],
      ["b", 1],
      ["c", null],
    ]);
  });

  it("names the author, with Claude's own label when there is one", () => {
    const views = toNoteViews(
      [note({ id: "a" }), note({ id: "b", author: "claude", author_label: "Claude Code" })],
      {},
    );
    expect(views.map((view) => view.authorLabel)).toEqual(["Le professeur", "Claude Code"]);
  });

  it("reads the lines a proposal targets from the open file, never rewriting it", () => {
    const files = { "main.py": "a\nb\nc\n" };
    const [view] = toNoteViews(
      [
        note({
          kind: "proposal",
          file_path: "main.py",
          line_start: 2,
          line_end: 2,
          replacement: "B",
        }),
      ],
      files,
    );
    expect(view?.before).toBe("b");
    expect(view?.replacement).toBe("B");
    expect(files["main.py"]).toBe("a\nb\nc\n");
  });
});

describe("toAnnotations", () => {
  it("keeps the annotations of the open file, and drops stale ones", () => {
    const views = toNoteViews(
      [
        note({ id: "1", kind: "annotation", file_path: "main.py", line_start: 3, content: "A" }),
        note({ id: "2", kind: "annotation", file_path: "util.py", line_start: 1 }),
        note({ id: "3", kind: "annotation", file_path: "main.py", line_start: 4, status: "stale" }),
        note({ id: "4", kind: "hint", file_path: "main.py", line_start: 2 }),
      ],
      {},
    );
    expect(toAnnotations(views, "main.py")).toEqual([{ id: "1", line: 3, text: "A" }]);
  });
});

describe("exercise states", () => {
  const sessions = [
    sessionSummary({ id: "s1", exercise_id: "e1", passed: false }),
    sessionSummary({ id: "s2", exercise_id: "e1", passed: true }),
    sessionSummary({ id: "s3", exercise_id: "e2" }),
    sessionSummary({ id: "s4", exercise_id: null, title: "Libre" }),
  ] as SessionSummary[];
  const exercises = ["e1", "e2", "e3"].map((id) => exerciseOut({ id })) as unknown as Exercise[];

  it("is passed if one session passed, doing if one exists, else todo", () => {
    const views = toExerciseViews(exercises, sessions);
    expect(views.map((view) => [view.id, view.state, view.sessionId])).toEqual([
      ["e1", "passed", "s1"],
      ["e2", "doing", "s3"],
      ["e3", "todo", null],
    ]);
  });

  it("lists the sessions without exercise apart", () => {
    expect(toFreeSessions(sessions)).toEqual([{ id: "s4", title: "Libre", passed: false }]);
  });
});

describe("isFailedRun", () => {
  it("fails on a non-zero code, a timeout, a kill or an error; never while running", () => {
    expect(isFailedRun({ status: "done", exit_code: 0 })).toBe(false);
    expect(isFailedRun({ status: "done", exit_code: 1 })).toBe(true);
    expect(isFailedRun({ status: "timeout", exit_code: null })).toBe(true);
    expect(isFailedRun({ status: "killed", exit_code: null })).toBe(true);
    expect(isFailedRun({ status: "error", exit_code: null })).toBe(true);
    expect(isFailedRun({ status: "running", exit_code: null })).toBe(false);
  });
});
