import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ExternalLink } from "./ExternalLink";

describe("ExternalLink", () => {
  it("opens in a new tab with noopener noreferrer and says so", () => {
    render(<ExternalLink href="https://example.org/a">Offre</ExternalLink>);
    const link = screen.getByRole("link", { name: "Offre (opens in a new tab)" });
    expect(link).toHaveAttribute("href", "https://example.org/a");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("never makes a link of an address that is not http or https", () => {
    render(<ExternalLink href="javascript:alert(1)">Offre</ExternalLink>);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Offre")).toBeInTheDocument();
  });
});
