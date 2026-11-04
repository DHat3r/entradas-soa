import { describe, expect, it } from "vitest";
import { cuentaRegresiva, diaYMes, pesos, precioDesde } from "./formato";

describe("pesos", () => {
  it("usa punto de miles y no muestra decimales", () => {
    expect(pesos(15000).replace(/\s/g, "")).toBe("$15.000");
  });
});

describe("cuentaRegresiva", () => {
  it("muestra minutos y segundos con dos dígitos", () => {
    expect(cuentaRegresiva(65_000)).toBe("1:05");
  });

  it("redondea hacia arriba para no mostrar 0:00 antes de tiempo", () => {
    expect(cuentaRegresiva(100)).toBe("0:01");
  });

  it("nunca muestra tiempo negativo", () => {
    expect(cuentaRegresiva(-5_000)).toBe("0:00");
  });
});

describe("diaYMes", () => {
  it("usa la zona horaria de Chile aunque en UTC ya sea otro día", () => {
    expect(diaYMes("2026-12-01T01:00:00Z").dia).toBe("30");
  });
});

describe("precioDesde", () => {
  it("devuelve el precio más bajo", () => {
    expect(precioDesde([30000, 15000, 22000])).toBe(15000);
  });
});
