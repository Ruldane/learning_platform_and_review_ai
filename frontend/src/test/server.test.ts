import { describe, expect, it, vi } from "vitest";

describe("serveur MSW partagé", () => {
  it("fait échouer toute requête sans handler avec l'erreur MSW (stratégie « error »)", async () => {
    const logged = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const failure = await fetch("http://localhost:8000/api/v1/sans-handler").catch(
      (e: unknown) => e,
    );
    const calls = logged.mock.calls.map((call) => String(call[0]));
    logged.mockRestore();

    expect(failure).toBeInstanceOf(Error);
    expect(String((failure as Error).cause)).toContain(
      'Cannot bypass a request when using the "error" strategy',
    );
    expect(calls.some((c) => c.includes("without a matching request handler"))).toBe(true);
  });
});
