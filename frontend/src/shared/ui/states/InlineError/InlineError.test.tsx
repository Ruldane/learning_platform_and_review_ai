import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InlineError } from "./InlineError";

describe("InlineError", () => {
  it("affiche le message dans une alerte", () => {
    render(<InlineError message="La clé est trop courte." />);
    expect(screen.getByRole("alert")).toHaveTextContent("La clé est trop courte.");
  });
});
