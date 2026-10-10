import { describe, expect, it } from "vitest";
import { escapeHtml, safeHttpUrl } from "../lib/html";

describe("html safety", () => {
  it("escapes markup and quotes", () => {
    expect(escapeHtml(`<img src=x onerror="alert('1')">`)).toBe(
      "&lt;img src=x onerror=&quot;alert(&#39;1&#39;)&quot;&gt;"
    );
  });

  it("treats null and numbers as text", () => {
    expect(escapeHtml(null)).toBe("");
    expect(escapeHtml(42)).toBe("42");
  });

  it("allows only http and https links", () => {
    expect(safeHttpUrl("https://eonet.gsfc.nasa.gov/x")).toBe("https://eonet.gsfc.nasa.gov/x");
    expect(safeHttpUrl("javascript:alert(1)")).toBeNull();
    expect(safeHttpUrl("data:text/html,hi")).toBeNull();
    expect(safeHttpUrl("not a url")).toBeNull();
    expect(safeHttpUrl(undefined)).toBeNull();
  });
});
