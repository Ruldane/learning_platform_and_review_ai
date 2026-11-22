import { describe, expect, it } from "vitest";
import { ResponseClock, concentrationDrop, type Observation } from "./concentration";

const worked = (milliseconds: number, missed = false): Observation => ({ milliseconds, missed });

describe("repères de concentration", () => {
  it("demande un début de séance et les deux variations", () => {
    const baseline = [worked(2_000), worked(3_000), worked(4_000)];
    const slower = [worked(6_000), worked(7_000), worked(8_000)];
    const mistakes = [worked(6_000, true), worked(7_000, true), worked(8_000)];
    expect(concentrationDrop([...baseline, ...mistakes.slice(0, 2)])).toBe(false);
    expect(concentrationDrop([...baseline, ...slower])).toBe(false);
    expect(
      concentrationDrop([
        ...baseline,
        ...mistakes.map((sample) => ({ ...sample, milliseconds: 3_500 })),
      ]),
    ).toBe(false);
    expect(concentrationDrop([...baseline, ...mistakes])).toBe(true);
    expect(
      concentrationDrop([
        ...baseline,
        ...mistakes.map((sample) => ({ ...sample, milliseconds: 2_000_000 })),
      ]),
    ).toBe(false);
  });

  it("écarte une réponse inactive, une interruption et une mesure trop courte", () => {
    let now = 0;
    const clock = new ResponseClock(() => now);
    clock.restart();
    now = 45_000;
    expect(clock.take()).toBeNull();
    now += 1_200;
    clock.activity();
    now += 1_300;
    expect(clock.take()).toBe(2_500);
    clock.interrupt();
    now += 2_000;
    expect(clock.take()).toBeNull();
    now += 50;
    expect(clock.take()).toBeNull();
  });

  it("mesure l’activité continue dans les bornes et redémarre après une pause", () => {
    let now = 0;
    const clock = new ResponseClock(() => now);
    clock.restart();
    for (let count = 0; count < 4; count += 1) {
      now += 25_000;
      clock.activity();
    }
    expect(clock.take()).toBeNull();
    now += 600_000;
    clock.restart();
    now += 1_000;
    expect(clock.take()).toBe(1_000);
  });
});
