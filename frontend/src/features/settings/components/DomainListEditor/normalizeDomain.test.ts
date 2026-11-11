import { describe, expect, it } from "vitest";
import { normalizeDomain } from "./normalizeDomain";

describe("normalizeDomain", () => {
  it.each([
    ["https://www.Python.org/doc", "python.org"],
    ["docs.python.org", "docs.python.org"],
    ["  HTTP://User@Example.COM:8080/a?b=c#d  ", "example.com"],
    ["www.github.com.", "github.com"],
    ["xn--bcher-kva.example", "xn--bcher-kva.example"],
  ])("normalise %s en %s", (value, expected) => {
    expect(normalizeDomain(value)).toBe(expected);
  });

  it.each([
    "",
    "   ",
    "localhost",
    "192.168.0.1",
    "a b.com",
    "-x.com",
    "exemple.c",
    "http://",
    "a..com",
  ])("refuse %j", (value) => {
    expect(normalizeDomain(value)).toBeNull();
  });
});
