import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { KeysSection } from "./KeysSection";

describe("KeysSection", () => {
  it("affiche le titre et une carte par fournisseur", () => {
    render(
      <KeysSection
        entries={[
          {
            provider: "anthropic",
            label: "Anthropic",
            source: "ui",
            last4: "1234",
            readable: true,
            last_test_ok: null,
          },
        ]}
        testResults={{}}
        pendingProviders={[]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onTest={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Clés API" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Anthropic" })).toBeInTheDocument();
  });
});
