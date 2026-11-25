const LABEL = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;
const TLD = /^([a-z]{2,63}|xn--[a-z0-9-]{1,59})$/;

/**
 * Reduces input to a domain name: lowercase, no scheme, credentials, path, query,
 * fragment, port, trailing dot or "www.". Returns `null` if it is not a domain (at least two
 * labels, alphabetic extension: IP addresses and "localhost" are refused). Same rule as
 * `normalize_domain` on the back end (`research/service/domains.py`).
 */
export function normalizeDomain(raw: string): string | null {
  let host = raw.trim().toLowerCase();
  host = host.replace(/^[a-z][a-z0-9+.-]*:\/\//, "");
  host = host.split(/[/?#]/, 1)[0] ?? "";
  host = host.slice(host.lastIndexOf("@") + 1);
  host = host.replace(/:\d*$/, "");
  host = host.replace(/\.$/, "").replace(/^www\./, "");
  if (host.length === 0 || host.length > 253) return null;
  const labels = host.split(".");
  if (labels.length < 2) return null;
  if (!labels.every((label) => LABEL.test(label))) return null;
  return TLD.test(labels.at(-1) ?? "") ? host : null;
}
