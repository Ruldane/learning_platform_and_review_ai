import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UsageBadge } from "./UsageBadge";

const usage = {
  sessionTokens: 12_340,
  dayTokens: 45_000,
  sessionCap: 100_000,
  dayCap: 300_000,
  onDemand: false,
};

describe("UsageBadge", () => {
  it("shows session and day consumption", () => {
    render(<UsageBadge usage={usage} />);
    expect(screen.getByText(/Session: 12,340 of 100,000 tokens/)).toBeInTheDocument();
    expect(screen.getByText(/Day: 45,000 of 300,000 tokens/)).toBeInTheDocument();
    expect(screen.queryByText("On request")).toBeNull();
  });

  it("says Sur demande in words when the teacher no longer answers alone", () => {
    render(<UsageBadge usage={{ ...usage, sessionTokens: 100_000, onDemand: true }} />);
    expect(screen.getByText("On request")).toBeInTheDocument();
    expect(screen.getByText("The professor no longer answers on its own.")).toBeInTheDocument();
  });
});
