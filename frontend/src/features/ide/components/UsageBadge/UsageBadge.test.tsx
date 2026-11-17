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
    expect(screen.getByText(/Séance : 12\s340 sur 100\s000 jetons/)).toBeInTheDocument();
    expect(screen.getByText(/Jour : 45\s000 sur 300\s000 jetons/)).toBeInTheDocument();
    expect(screen.queryByText("Sur demande")).toBeNull();
  });

  it("says Sur demande in words when the teacher no longer answers alone", () => {
    render(<UsageBadge usage={{ ...usage, sessionTokens: 100_000, onDemand: true }} />);
    expect(screen.getByText("Sur demande")).toBeInTheDocument();
    expect(screen.getByText("Le professeur ne répond plus tout seul.")).toBeInTheDocument();
  });
});
