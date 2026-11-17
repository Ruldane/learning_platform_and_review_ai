import { expectTypeOf, it } from "vitest";
import type { Choice } from "./components/ClaimChoice";
import type { ClaimChoice } from "./types";

it("the claim screen offers exactly the choices of the generated contract", () => {
  expectTypeOf<Choice>().toEqualTypeOf<ClaimChoice>();
});
