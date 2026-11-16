import { beforeEach, describe, expect, it } from "vitest";
import { useCaptureRequest } from "./captureRequest";

describe("useCaptureRequest", () => {
  beforeEach(() => useCaptureRequest.setState({ count: 0 }));

  it("counts the requests", () => {
    useCaptureRequest.getState().request();
    useCaptureRequest.getState().request();
    expect(useCaptureRequest.getState().count).toBe(2);
  });
});
