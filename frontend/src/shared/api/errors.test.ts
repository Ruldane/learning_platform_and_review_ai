import { describe, expect, it } from "vitest";
import { ApiError, errorMessage } from "./errors";

const GENERIC = "Something went wrong. Try again in a moment.";

describe("errorMessage", () => {
  it("returns the message from an ApiError", () => {
    const error = new ApiError({
      code: "invalid_key",
      message: "The key is too short.",
      status: 422,
    });
    expect(errorMessage(error)).toBe("The key is too short.");
  });

  it("returns the generic message for other errors", () => {
    expect(errorMessage(new Error("boom"))).toBe(GENERIC);
    expect(errorMessage("text")).toBe(GENERIC);
  });
});
