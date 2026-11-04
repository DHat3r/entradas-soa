import { describe, expect, it } from "vitest";
import { rutaSegura } from "./sesion";

describe("rutaSegura", () => {
  it("acepta rutas internas", () => {
    expect(rutaSegura("/mis-entradas", "/")).toBe("/mis-entradas");
    expect(rutaSegura("/eventos/1?a=b", "/")).toBe("/eventos/1?a=b");
  });

  it.each(["https://malo.cl", "//malo.cl", "/\\malo.cl", "/\t/malo.cl", "javascript:alert(1)", null])(
    "rechaza %s y usa la ruta por defecto",
    (volver) => {
      expect(rutaSegura(volver, "/")).toBe("/");
    },
  );
});
