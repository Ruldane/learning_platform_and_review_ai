import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/api/errors";
import { failureReason, launchErrors, openRunId } from "./errors";

const refusal = (code: string, status: number, details: unknown = null) =>
  new ApiError({ code, message: "Message du serveur.", status, details });

describe("openRunId", () => {
  it("reads the running run of a 409 radar_in_progress", () => {
    expect(openRunId(refusal("radar_in_progress", 409, { run_id: "r9" }))).toBe("r9");
  });

  it("ignores any other refusal and a 409 without an identifier", () => {
    expect(openRunId(refusal("radar_role_required", 409))).toBeNull();
    expect(openRunId(refusal("radar_in_progress", 409, {}))).toBeNull();
    expect(openRunId(new Error("réseau"))).toBeNull();
  });
});

describe("launchErrors", () => {
  it("puts a missing role on the role field", () => {
    expect(launchErrors(refusal("radar_role_required", 409))).toEqual({
      role: "Indique le poste visé pour lancer un relevé.",
    });
  });

  it("names the refused fields of a 422 and nothing else", () => {
    const errors = launchErrors(refusal("validation_error", 422, { fields: ["role", "zone"] }));
    expect(errors.role).toContain("entre 2 et 120");
    expect(errors.zone).toContain("entre 2 et 120");
    expect(errors.general).toBeUndefined();
  });

  it("keeps any other refusal as a general message", () => {
    expect(launchErrors(refusal("engine_unavailable", 503)).general).toBe("Message du serveur.");
  });
});

describe("failureReason", () => {
  it("explains every known code and falls back for the others", () => {
    expect(failureReason("session_cancelled")).toBe("le relevé a été arrêté avant la fin.");
    expect(failureReason("llm_unavailable")).toBe(
      "aucun modèle n'est utilisable (clé absente ?) : rien n'a été lu.",
    );
    expect(failureReason("RuntimeError")).toBe("une panne inattendue a interrompu le relevé.");
    expect(failureReason(null)).toBe("une panne inattendue a interrompu le relevé.");
  });
});
