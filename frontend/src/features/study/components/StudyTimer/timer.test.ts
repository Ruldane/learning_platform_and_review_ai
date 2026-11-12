import { describe, expect, it } from "vitest";
import { advance, initialTimer } from "./timer";

const WORK = 50 * 60;
const BREAK = 10 * 60;

describe("timer model", () => {
  it("starts running at the full work duration", () => {
    expect(initialTimer(WORK)).toEqual({
      phase: "work",
      secondsLeft: WORK,
      workedSeconds: 0,
      running: true,
    });
  });

  it("counts work seconds only", () => {
    const afterWork = advance(initialTimer(WORK), WORK, WORK, BREAK);
    expect(afterWork).toMatchObject({ phase: "break", secondsLeft: BREAK, workedSeconds: WORK });
    const afterBreak = advance(afterWork, 120, WORK, BREAK);
    expect(afterBreak).toMatchObject({
      phase: "break",
      secondsLeft: BREAK - 120,
      workedSeconds: WORK,
    });
  });

  it("carries the remainder over a phase change", () => {
    const state = advance(initialTimer(WORK), WORK + BREAK + 30, WORK, BREAK);
    expect(state).toMatchObject({
      phase: "work",
      secondsLeft: WORK - 30,
      workedSeconds: WORK + 30,
    });
  });

  it("changes nothing for a zero or negative step", () => {
    const start = initialTimer(WORK);
    expect(advance(start, 0, WORK, BREAK)).toEqual(start);
    expect(advance(start, -5, WORK, BREAK)).toEqual(start);
  });
});
