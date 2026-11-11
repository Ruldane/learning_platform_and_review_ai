import { describe, expect, it } from "vitest";
import { ApiError, errorMessage } from "./errors";

const GENERIC = "Une erreur est survenue. Réessaie dans un instant.";

describe("errorMessage", () => {
  it("renvoie le message français d'une ApiError", () => {
    const error = new ApiError({
      code: "invalid_key",
      message: "La clé est trop courte.",
      status: 422,
    });
    expect(errorMessage(error)).toBe("La clé est trop courte.");
  });

  it("renvoie le message général pour toute autre erreur", () => {
    expect(errorMessage(new Error("boom"))).toBe(GENERIC);
    expect(errorMessage("texte")).toBe(GENERIC);
  });
});
