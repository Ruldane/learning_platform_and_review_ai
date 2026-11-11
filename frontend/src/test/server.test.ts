import { describe, expect, it } from "vitest";

describe("serveur MSW partagé", () => {
  it("fait échouer toute requête sans handler", async () => {
    await expect(fetch("http://localhost:8000/api/v1/sans-handler")).rejects.toThrow();
  });
});
