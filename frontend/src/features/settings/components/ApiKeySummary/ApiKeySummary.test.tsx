import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ApiKeyEntry } from "../viewTypes";
import { ApiKeySummary } from "./ApiKeySummary";

const entry: ApiKeyEntry = {
  provider: "anthropic",
  label: "Anthropic",
  source: "ui",
  last4: "1234",
  readable: true,
  last_test_ok: true,
};

describe("ApiKeySummary", () => {
  it("shows the provider, the last four characters, and the source", () => {
    render(<ApiKeySummary entry={entry} headingId="titre" />);
    expect(screen.getByRole("heading", { name: "Anthropic" })).toHaveAttribute("id", "titre");
    expect(screen.getByText("•••• 1234")).toBeInTheDocument();
    expect(screen.getByText("entered here")).toBeInTheDocument();
    expect(screen.getByText("Last test: passed")).toBeInTheDocument();
  });

  it("explains how to remove a key that comes from the .env file", () => {
    render(<ApiKeySummary entry={{ ...entry, source: "env" }} headingId="titre" />);
    expect(screen.getByText(".env file")).toBeInTheDocument();
    expect(screen.getByText(/remove it from that file/)).toBeInTheDocument();
  });

  it("reports a missing key", () => {
    render(
      <ApiKeySummary
        entry={{ ...entry, source: null, last4: null, last_test_ok: null }}
        headingId="titre"
      />,
    );
    expect(screen.getByText("No key saved")).toBeInTheDocument();
    expect(screen.queryByText(/^Last test:/)).not.toBeInTheDocument();
  });

  it("reports an unreadable key", () => {
    render(<ApiKeySummary entry={{ ...entry, readable: false }} headingId="titre" />);
    expect(screen.getByText("Unreadable key, enter it again")).toBeInTheDocument();
  });
});
