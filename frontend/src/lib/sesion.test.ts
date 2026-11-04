import { describe, expect, it } from "vitest";
import { rutaSegura } from "./sesion";

describe("rutaSegura", () => {
  it("acepta rutas internas", () => {
    expect(rutaSegura("/mis-entradas", "/")).toBe("/mis-entradas");
  });

  it.each(["https://malo.cl", "//malo.cl", "/\\malo.cl", "javascript:alert(1)", null])(
    "rechaza %s y usa la ruta por defecto",
    (volver) => {
      expect(rutaSegura(volver, "/")).toBe("/");
    },
  );
});
