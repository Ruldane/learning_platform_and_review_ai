import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { STATUS_ORDER } from "../viewTypes";
import { StatusBadge } from "./StatusBadge";

const LABELS = [
  "To apply",
  "Applied",
  "Relancée",
  "Interview",
  "Offer",
  "Refus",
  "Sans réponse",
  "Retirée",
];

describe("StatusBadge", () => {
  it("writes the status out in French, whatever the status", () => {
    STATUS_ORDER.forEach((status, index) => {
      const { unmount } = render(<StatusBadge status={status} />);
      expect(screen.getByText(LABELS[index] as string)).toBeInTheDocument();
      unmount();
    });
  });

  it("carries the status as a data attribute for styling and tests", () => {
    render(<StatusBadge status="offer" />);
    expect(screen.getByText("Offer")).toHaveAttribute("data-status", "offer");
  });
});
