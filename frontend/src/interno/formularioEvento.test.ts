import { describe, expect, it } from "vitest";
import { aDatosDeEvento, type FormularioEvento } from "./formularioEvento";

const formulario: FormularioEvento = {
  nombre: "  Festival de otoño  ",
  lugar: " Parque Forestal ",
  fecha: "2026-12-01T20:00",
  descripcion: "  Música en vivo  ",
  sectores: [
    { nombre: " General ", precio: "15000", capacidad: "300" },
    { nombre: "VIP", precio: "45000", capacidad: "40" },
  ],
};

describe("aDatosDeEvento", () => {
  it("convierte precio y capacidad de texto a número", () => {
    const datos = aDatosDeEvento(formulario);

    expect(datos.sectores[0].precio_clp).toBe(15000);
    expect(datos.sectores[0].capacidad).toBe(300);
    expect(typeof datos.sectores[1].precio_clp).toBe("number");
  });

  it("convierte la fecha local a ISO en UTC", () => {
    const datos = aDatosDeEvento(formulario);

    expect(datos.fecha).toBe(new Date("2026-12-01T20:00").toISOString());
  });

  it("quita espacios sobrantes de nombres y textos", () => {
    const datos = aDatosDeEvento(formulario);

    expect(datos.nombre).toBe("Festival de otoño");
    expect(datos.lugar).toBe("Parque Forestal");
    expect(datos.descripcion).toBe("Música en vivo");
    expect(datos.sectores[0].nombre).toBe("General");
  });

  it("conserva el orden y la cantidad de sectores", () => {
    const datos = aDatosDeEvento(formulario);

    expect(datos.sectores.map((sector) => sector.nombre)).toEqual(["General", "VIP"]);
  });
});
