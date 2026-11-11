import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/server";
import { api, apiBaseUrl } from "./client";
import { ApiError, unwrap } from "./errors";

const ME_URL = `${apiBaseUrl}/api/v1/auth/me`;

describe("client API", () => {
  it("transforme une erreur API en ApiError", async () => {
    server.use(
      http.get(ME_URL, () =>
        HttpResponse.json(
          { error: { code: "auth_required", message: "Connexion requise.", details: null } },
          { status: 401 },
        ),
      ),
    );
    await expect(api.GET("/auth/me").then(unwrap)).rejects.toMatchObject({
      code: "auth_required",
      status: 401,
      message: "Connexion requise.",
    });
  });

  it("rejette avec une instance d'ApiError portant les détails", async () => {
    server.use(
      http.get(ME_URL, () =>
        HttpResponse.json(
          { error: { code: "invalid", message: "Invalide.", details: [{ loc: ["body"] }] } },
          { status: 422 },
        ),
      ),
    );
    const error = await api.GET("/auth/me").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).details).toEqual([{ loc: ["body"] }]);
  });

  it("transforme une réponse 500 sans JSON en ApiError générique", async () => {
    server.use(http.get(ME_URL, () => new HttpResponse("<html>boom</html>", { status: 500 })));
    await expect(api.GET("/auth/me").then(unwrap)).rejects.toMatchObject({
      code: "http_error",
      status: 500,
      message: "Une erreur est survenue. Réessaie dans un instant.",
    });
  });

  it("transforme une panne réseau en ApiError", async () => {
    server.use(http.get(ME_URL, () => HttpResponse.error()));
    await expect(api.GET("/auth/me")).rejects.toMatchObject({
      code: "network_error",
      status: 0,
    });
  });

  it("renvoie les données d'une réponse réussie", async () => {
    server.use(http.get(`${apiBaseUrl}/api/v1/health`, () => HttpResponse.json({ status: "ok" })));
    const body = unwrap(await api.GET("/health"));
    expect(body).toMatchObject({ status: "ok" });
  });
});

describe("unwrap", () => {
  it("convertit une erreur restée dans le résultat en ApiError", () => {
    const result = {
      error: { error: { code: "x", message: "Oups.", details: null } },
      response: new Response(null, { status: 400 }),
    };
    expect(() => unwrap(result)).toThrowError(expect.objectContaining({ code: "x", status: 400 }));
  });
});
