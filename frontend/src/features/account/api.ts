import { api, apiBaseUrl } from "@/shared/api/client";
import { ApiError, unwrap } from "@/shared/api/errors";
import type { Me } from "./types";

/**
 * The archive address: a plain link, never a `fetch` call (the browser downloads the
 * zip and takes its name from the `Content-Disposition` header of the backend: `tremplin-export-
 * AAAAMMJJ.zip`).
 */
export const exportUrl = `${apiBaseUrl}/api/v1/account/export`;

/** Clears the displayed account. A 202 means the final vector purge is pending. */
export async function postDeleteAccount(confirm: string, expectedUserId: string) {
  unwrap(
    await api.POST("/account/delete", {
      body: { confirm, expected_user_id: expectedUserId },
    }),
  );
}

/**
 * `GET /auth/me`, read only for the mode (`local` or `google`). A 401 `auth_required` means
 * « pas de session » (`null`), as for the login gate that shares this read key.
 */
export async function fetchMe(signal?: AbortSignal): Promise<Me | null> {
  try {
    return unwrap(await api.GET("/auth/me", { signal }));
  } catch (error) {
    if (error instanceof ApiError && error.code === "auth_required") return null;
    throw error;
  }
}

/** The signed-in account is no longer the one displayed: no deletion has started. */
export class AccountChangedError extends Error {
  constructor() {
    super("account_changed");
    this.name = "AccountChangedError";
  }
}
