import { http, HttpResponse } from "msw";
import { errorBody } from "./authApi";
import { API } from "./councilApi";

interface AccountApiOptions {
  /**
   * Réponse de `POST /account/delete` : `ok` (204), `refused` (422 `confirmation_required`, qui ne
   * renvoie jamais la saisie), `down` (500) ou `wrong-code` (422 d'un autre code).
   */
  delete?: "ok" | "refused" | "down" | "wrong-code";
}

/** Faux serveur de « Mes données » ; garde les corps reçus par la suppression. */
export function accountApi(options: AccountApiOptions = {}) {
  const deleteBodies: unknown[] = [];
  const handlers = [
    http.post(`${API}/account/delete`, async ({ request }) => {
      deleteBodies.push(await request.json());
      switch (options.delete ?? "ok") {
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
