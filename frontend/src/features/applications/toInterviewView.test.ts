import { describe, expect, it } from "vitest";
import { debriefOut, interviewOut } from "@/test/interviewApi";
import { toInterviewView } from "./toInterviewView";
import type { InterviewOut } from "./types";

const view = (scores: Record<string, number>) =>
  toInterviewView(interviewOut({ debrief: debriefOut({ scores }) }) as unknown as InterviewOut);

describe("toInterviewView", () => {
  it("keeps a score the model did not give as unknown, never as a real 0", () => {
    const scores = view({ clarte: 4, structure: 3, adequation: 5 }).debrief?.scores;
    expect(scores).toEqual([
      { key: "clarte", value: 4 },
      { key: "structure", value: 3 },
      { key: "profondeur_technique", value: null },
      { key: "adequation", value: 5 },
    ]);
  });
});
