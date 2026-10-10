import { describe, expect, it } from "vitest";
import { speechLang, translate } from "../lib/i18n";

describe("i18n", () => {
  it("returns Spanish strings when asked", () => {
    expect(translate("es", "send")).toBe("Preguntar");
    expect(translate("en", "send")).toBe("Ask");
  });

  it("maps locales to speech voices", () => {
    expect(speechLang("es")).toBe("es-US");
    expect(speechLang("en")).toBe("en-US");
  });
});
