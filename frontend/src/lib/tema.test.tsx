import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BotonTema, ProveedorDeTema } from "./tema";

function mostrarBoton() {
  render(
    <ProveedorDeTema>
      <BotonTema />
    </ProveedorDeTema>,
  );
}

describe("BotonTema", () => {
  beforeEach(() => {
    document.documentElement.dataset.tema = "oscuro";
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("parte con el tema que dejó el script de index.html", () => {
    document.documentElement.dataset.tema = "claro";

    mostrarBoton();

    expect(screen.getByRole("button", { name: "Cambiar a modo oscuro" })).toBeTruthy();
  });

  it("cambia el tema del documento y recuerda la elección", () => {
    mostrarBoton();

    fireEvent.click(screen.getByRole("button", { name: "Cambiar a modo claro" }));

    expect(document.documentElement.dataset.tema).toBe("claro");
    expect(localStorage.getItem("tema")).toBe("claro");
    expect(screen.getByRole("button", { name: "Cambiar a modo oscuro" })).toBeTruthy();
  });

  it("sigue funcionando si el navegador no permite guardar", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("Almacenamiento bloqueado");
    });
    mostrarBoton();

    fireEvent.click(screen.getByRole("button", { name: "Cambiar a modo claro" }));

    expect(document.documentElement.dataset.tema).toBe("claro");
  });
});
