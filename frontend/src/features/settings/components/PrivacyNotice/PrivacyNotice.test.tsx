import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PrivacyNotice } from "./PrivacyNotice";

describe("PrivacyNotice", () => {
  it("lists what leaves the machine, and where it goes (17.3)", () => {
    render(<PrivacyNotice />);
    const table = screen.getByRole("table", { name: "What leaves your machine" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(
      rows.map((row) =>
        within(row)
          .getAllByRole("cell")
          .map((c) => c.textContent),
      ),
    ).toEqual([
      [
        "Prompts, which may contain your CV and your profile",
        "The model provider you choose",
      ],
      ["Search queries", "The engines queried by SearXNG"],
      ["Everything else (database, vectors, files, embeddings)", "Stays on your machine"],
    ]);
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((c) => c.textContent),
    ).toEqual(["Data", "Destination"]);
  });

  it("says what is removed from searches and what contacts keep", () => {
    render(<PrivacyNotice />);
    expect(
      screen.getByText(/removes your name, email and phone number from queries/),
    ).toBeInTheDocument();
    expect(screen.getByText(/limited to a name, a role and a public link/)).toBeInTheDocument();
    expect(screen.getByText(/export or delete everything/)).toBeInTheDocument();
  });
});
