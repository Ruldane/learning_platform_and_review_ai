import { http, HttpResponse } from "msw";
import { errorBody } from "./authApi";
import { API } from "./councilApi";

interface AccountApiOptions {
  /**
   * Réponse de `POST /account/delete` : `ok` (204), `refused` (422 `confirmation_required`, qui ne
   * renvoie jamais la saisie), `down` (500), `wrong-code` (422 d'un autre code), `unavailable`
   * (503 `vector_store_unavailable`, avant toute suppression), `expired` (401) ou `network`.
   */
  delete?: "ok" | "refused" | "down" | "wrong-code" | "unavailable" | "expired" | "network";
  /** Tient la réponse de la suppression jusqu'à l'ouverture de la porte. */
  gate?: Promise<void>;
  /** Reçoit « delete » quand la suppression arrive : pour l'ordre des appels. */
  order?: string[];
}

/** Faux serveur de « Mes données » ; garde les corps reçus par la suppression. */
export function accountApi(options: AccountApiOptions = {}) {
  const deleteBodies: unknown[] = [];
  const handlers = [
    http.post(`${API}/account/delete`, async ({ request }) => {
      deleteBodies.push(await request.json());
      options.order?.push("delete");
      await options.gate;
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
