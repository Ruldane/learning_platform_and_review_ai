import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StudyTimer } from "./StudyTimer";

const MINUTE = 60_000;

function lastWorked(spy: ReturnType<typeof vi.fn>): number | undefined {
  return spy.mock.calls.at(-1)?.[0] as number | undefined;
}

function pass(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

describe("StudyTimer", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("starts on the work phase and counts down", () => {
    render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={vi.fn()} />);
    expect(screen.getByRole("timer")).toHaveTextContent("50:00");
    expect(screen.getByText("Travail")).toBeInTheDocument();
    pass(90_000);
    expect(screen.getByRole("timer")).toHaveTextContent("48:30");
  });

  it("switches to break after 50 minutes and counts only work", () => {
    const onWorked = vi.fn();
    render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={onWorked} />);
    pass(50 * MINUTE);
    expect(screen.getByText("Pause")).toBeInTheDocument();
    expect(screen.getByRole("timer")).toHaveTextContent("10:00");
    expect(lastWorked(onWorked)).toBe(3000);
    pass(10 * MINUTE);
    expect(screen.getByText("Travail")).toBeInTheDocument();
    expect(lastWorked(onWorked)).toBe(3000);
    pass(MINUTE);
    expect(lastWorked(onWorked)).toBe(3060);
  });

  it("follows the configured cycle lengths", () => {
    render(<StudyTimer workMinutes={25} breakMinutes={5} onWorkedChange={vi.fn()} />);
    expect(screen.getByRole("timer")).toHaveTextContent("25:00");
    pass(25 * MINUTE);
    expect(screen.getByRole("timer")).toHaveTextContent("05:00");
  });

  it("pauses and resumes", () => {
    const onWorked = vi.fn();
    render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={onWorked} />);
    pass(MINUTE);
    fireEvent.click(screen.getByRole("button", { name: "Mettre en pause" }));
    pass(5 * MINUTE);
    expect(screen.getByRole("timer")).toHaveTextContent("49:00");
    expect(lastWorked(onWorked)).toBe(60);
    expect(screen.getByText("Minuteur en pause")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reprendre" }));
    pass(30_000);
    expect(lastWorked(onWorked)).toBe(90);
    expect(screen.getByRole("button", { name: "Mettre en pause" })).toBeInTheDocument();
  });

  it("announces phase changes politely", () => {
    render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={vi.fn()} />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toBeEmptyDOMElement();
    pass(50 * MINUTE);
    expect(status).toHaveTextContent("Pause de 10 min");
    pass(10 * MINUTE);
    expect(status).toHaveTextContent("reprise du travail");
  });

  it("does not announce the countdown itself", () => {
    render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={vi.fn()} />);
    pass(30_000);
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });

  it("never adds more than a minute for one tick (sleeping computer)", () => {
    const onWorked = vi.fn();
    render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={onWorked} />);
    act(() => {
      vi.setSystemTime(Date.now() + 3 * 60 * MINUTE);
      vi.advanceTimersByTime(1000);
    });
    expect(lastWorked(onWorked)).toBe(60);
  });

  it("shows the worked time", () => {
    render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={vi.fn()} />);
    pass(12 * MINUTE);
    expect(screen.getByText("Temps travaillé : 12 min")).toBeInTheDocument();
  });

  it("uses motion only where the user allows it", () => {
    const { container } = render(
      <StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={vi.fn()} />,
    );
    const bare = Array.from(container.querySelectorAll("[class]:not([data-slot=button])"))
      .flatMap((node) => node.getAttribute("class")?.split(/\s+/) ?? [])
      .filter((name) => /^(transition|animate|duration)/.test(name));
    expect(bare).toEqual([]);
  });

  describe("kept across a reload (revue finale 5, E-I2 et E-m8)", () => {
    const key = "study-timer:st1";
    afterEach(() => window.sessionStorage.clear());

    it("takes the worked time back after an unmount", () => {
      const first = render(
        <StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={vi.fn()} storageKey={key} />,
      );
      pass(10 * MINUTE);
      first.unmount();
      const onWorked = vi.fn();
      render(
        <StudyTimer
          workMinutes={50}
          breakMinutes={10}
          onWorkedChange={onWorked}
          storageKey={key}
        />,
      );
      expect(lastWorked(onWorked)).toBe(600);
      expect(screen.getByRole("timer")).toHaveTextContent("40:00");
      pass(MINUTE);
      expect(lastWorked(onWorked)).toBe(660);
    });

    it("starts fresh when the stored timer is unreadable or the storage refuses", () => {
      window.sessionStorage.setItem(key, "{pas du json");
      const onWorked = vi.fn();
      const { unmount } = render(
        <StudyTimer
          workMinutes={50}
          breakMinutes={10}
          onWorkedChange={onWorked}
          storageKey={key}
        />,
      );
      expect(screen.getByRole("timer")).toHaveTextContent("50:00");
      unmount();
      const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
        throw new Error("refusé");
      });
      render(
        <StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={vi.fn()} storageKey={key} />,
      );
      expect(screen.getByRole("timer")).toHaveTextContent("50:00");
      spy.mockRestore();
    });

    it("stops the clock while halted", () => {
      const onWorked = vi.fn();
      render(<StudyTimer workMinutes={50} breakMinutes={10} onWorkedChange={onWorked} halted />);
      pass(5 * MINUTE);
      expect(screen.getByRole("timer")).toHaveTextContent("50:00");
      expect(onWorked).not.toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "Reprendre" })).toBeDisabled();
    });
  });
});
