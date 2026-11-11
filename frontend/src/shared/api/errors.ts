import { t } from "@/shared/i18n/t";

/** Erreur renvoyée par le back au format `{"error": {"code", "message", "details"}}`. */
export class ApiError extends Error {
  code: string;
  details: unknown;
  status: number;

  constructor(init: { code: string; message: string; status: number; details?: unknown }) {
    super(init.message);
    this.name = "ApiError";
    this.code = init.code;
    this.details = init.details ?? null;
    this.status = init.status;
  }
}

interface Envelope {
  code: string;
  message: string;
  details: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Lit l'enveloppe d'erreur du back ; `null` si le corps n'a pas ce format. */
export function parseEnvelope(body: unknown): Envelope | null {
  if (!isRecord(body) || !isRecord(body.error)) return null;
  const { code, message, details } = body.error;
  if (typeof code !== "string" || typeof message !== "string") return null;
  return { code, message, details };
}

export function genericError(status: number): ApiError {
  return new ApiError({ code: "http_error", message: t("errors.generic"), status });
}

export function networkError(): ApiError {
  return new ApiError({ code: "network_error", message: t("errors.network"), status: 0 });
}

/** Construit l'`ApiError` d'une réponse en échec (corps JSON du back, sinon message générique). */
export async function errorFromResponse(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.clone().json();
  } catch {
    // Corps absent ou qui n'est pas du JSON (ex. page HTML d'un 500) : message générique.
  }
  const envelope = parseEnvelope(body);
  if (!envelope) return genericError(response.status);
  return new ApiError({ ...envelope, status: response.status });
}

/** Renvoie `data` ; lève une `ApiError` si le résultat contient une erreur. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined) {
    const envelope = parseEnvelope(result.error);
    if (!envelope) throw genericError(result.response.status);
    throw new ApiError({ ...envelope, status: result.response.status });
  }
  return result.data as T;
}
