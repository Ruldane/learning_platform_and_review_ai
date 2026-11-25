import { http, HttpResponse } from "msw";
import { errorBody } from "./authApi";
import { API } from "./councilApi";

interface AccountApiOptions {
  /**
   * Response of `POST /account/delete`: `ok` (204), `refused` (422 `confirmation_required`, which
   * never returns the input), `down` (500), `wrong-code` (422 of another code), `unavailable`
   * (503 `vector_store_unavailable`, before any deletion), `expired` (401) or `network`.
   */
  delete?:
    "ok" | "pending" | "refused" | "down" | "wrong-code" | "unavailable" | "expired" | "network";
  /** Holds the deletion response until the gate opens. */
  gate?: Promise<void>;
  /** Receives « delete » when the deletion arrives: for the order of calls. */
  order?: string[];
}

/** Fake « Mes données » server; keeps the bodies received by the deletion. */
export function accountApi(options: AccountApiOptions = {}) {
  const deleteBodies: unknown[] = [];
  const handlers = [
    http.post(`${API}/account/delete`, async ({ request }) => {
      deleteBodies.push(await request.json());
      options.order?.push("delete");
      await options.gate;
      switch (options.delete ?? "ok") {
        case "pending":
          return new HttpResponse(null, { status: 202, headers: { "Content-Length": "0" } });
        case "refused":
          return HttpResponse.json(
            errorBody("confirmation_required", "La confirmation n'est pas exacte.", {
              fields: ["confirm"],
            }),
            { status: 422 },
          );
        case "wrong-code":
          return HttpResponse.json(errorBody("validation_error", "Requête refusée."), {
            status: 422,
          });
        case "unavailable":
          return HttpResponse.json(
            errorBody("vector_store_unavailable", "La mémoire ne répond pas."),
            { status: 503 },
          );
        case "expired":
          return HttpResponse.json(errorBody("auth_required", "Connexion requise."), {
            status: 401,
          });
        case "network":
          return HttpResponse.error();
        case "down":
          return HttpResponse.json(errorBody("vector_unavailable", "La mémoire ne répond pas."), {
            status: 500,
          });
        default:
          return new HttpResponse(null, { status: 204 });
      }
    }),
  ];
  return { handlers, deleteBodies };
}
