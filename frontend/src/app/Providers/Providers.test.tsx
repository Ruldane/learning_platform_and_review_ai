import { useQueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createQueryClient, Providers } from "./Providers";

function Probe() {
  const defaults = useQueryClient().getDefaultOptions().queries;
  return (
    <p>{`retry=${String(defaults?.retry)} focus=${String(defaults?.refetchOnWindowFocus)}`}</p>
  );
}

describe("Providers", () => {
  it("fournit un client de requêtes aux enfants", () => {
    render(
      <Providers>
        <Probe />
      </Providers>,
    );
    expect(screen.getByText("retry=1 focus=false")).toBeInTheDocument();
  });

  it("crée un client distinct à chaque appel", () => {
    expect(createQueryClient()).not.toBe(createQueryClient());
  });
});
