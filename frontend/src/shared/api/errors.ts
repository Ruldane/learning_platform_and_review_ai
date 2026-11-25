import { t } from "@/shared/i18n/t";

/** Error returned by the back in the format `{"error": {"code", "message", "details"}}`. */
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

/** Reads the back's error envelope; `null` if the body does not have this format. */
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

/** Builds the `ApiError` of a failed response (JSON body from the back, else a generic message). */
export async function errorFromResponse(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.clone().json();
  } catch {
    // Empty body or non-JSON (e.g. an HTML 500 page): generic message.
  }
  const envelope = parseEnvelope(body);
  if (!envelope) return genericError(response.status);
  return new ApiError({ ...envelope, status: response.status });
}

/** Returns `data`; throws an `ApiError` if the result contains an error. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined) {
    const envelope = parseEnvelope(result.error);
    if (!envelope) throw genericError(result.response.status);
    throw new ApiError({ ...envelope, status: result.response.status });
  }
  return result.data as T;
}

/** French message to show for an error: the back's text for an `ApiError`, else the generic one. */
export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : t("errors.generic");
}
