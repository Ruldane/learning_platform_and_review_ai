import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import type { FeatureManifest } from "@/shared/lib/feature";
import { ShellGates } from "./ShellGates";

function gate(name: string, open = true) {
  return function Gate({ children }: { children: ReactNode }) {
    return open ? <section aria-label={name}>{children}</section> : <p>{`${name} ferme`}</p>;
  };
}

const plain: FeatureManifest = { id: "plain", routes: [] };

describe("ShellGates", () => {
  it("wraps the layout in the gates of the features, the first one outermost", () => {
    const features: FeatureManifest[] = [
      { id: "auth", routes: [], shell: { gate: gate("Connexion") } },
      plain,
      { id: "onboarding", routes: [], shell: { gate: gate("Premier lancement") } },
    ];
    render(
      <ShellGates features={features}>
        <p>Mise en page</p>
      </ShellGates>,
    );
    const outer = screen.getByRole("region", { name: "Connexion" });
    const inner = screen.getByRole("region", { name: "Premier lancement" });
    expect(outer).toContainElement(inner);
    expect(inner).toContainElement(screen.getByText("Mise en page"));
  });

  it("keeps the layout away while a gate stays closed, and renders it without gates", () => {
    const { rerender } = render(
      <ShellGates
        features={[{ id: "auth", routes: [], shell: { gate: gate("Connexion", false) } }]}
      >
        <p>Mise en page</p>
      </ShellGates>,
    );
    expect(screen.getByText("Connexion ferme")).toBeInTheDocument();
    expect(screen.queryByText("Mise en page")).toBeNull();
    rerender(
      <ShellGates features={[plain]}>
        <p>Mise en page</p>
      </ShellGates>,
    );
    expect(screen.getByText("Mise en page")).toBeInTheDocument();
  });
});
