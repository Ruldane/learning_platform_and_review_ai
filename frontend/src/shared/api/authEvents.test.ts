import { describe, expect, it, vi } from "vitest";
import { emitAuthRequired, onAuthRequired } from "./authEvents";

describe("authEvents", () => {
  it("prévient chaque écouteur, jusqu'à ce qu'il se désabonne", () => {
    const first = vi.fn();
    const second = vi.fn();
    const stopFirst = onAuthRequired(first);
    const stopSecond = onAuthRequired(second);
    emitAuthRequired();
    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(1);
    stopFirst();
    emitAuthRequired();
    expect(first).toHaveBeenCalledTimes(1);
    expect(second).toHaveBeenCalledTimes(2);
    stopSecond();
  });

  it("supporte un écouteur qui se désabonne pendant l'émission", () => {
    const calls: string[] = [];
    const stop = onAuthRequired(() => {
      calls.push("a");
      stop();
    });
    const stopB = onAuthRequired(() => calls.push("b"));
    emitAuthRequired();
    expect(calls).toEqual(["a", "b"]);
    stopB();
  });
});
