import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Rol } from "../lib/api";
import { useSesion } from "../lib/sesion";
import { PieDePagina } from "./PieDePagina";

vi.mock("../lib/sesion", () => ({ useSesion: vi.fn() }));

function mostrarCon(rol: Rol | null) {
  vi.mocked(useSesion).mockReturnValue({
    usuario: rol && { usuario_id: "u1", rol, correo: "a@b.cl", nombre: "Ana" },
    cargando: false,
    refrescar: vi.fn(),
    salir: vi.fn(),
  });
  render(
    <MemoryRouter>
      <PieDePagina />
    </MemoryRouter>,
  );
}

const hayEnlace = (nombre: string) => screen.queryByRole("link", { name: nombre }) !== null;

describe("PieDePagina", () => {
  afterEach(cleanup);

  it("sin sesión ofrece crear cuenta y el acceso del equipo", () => {
    mostrarCon(null);

    expect(hayEnlace("Crear cuenta")).toBe(true);
    expect(hayEnlace("Mis entradas")).toBe(true);
    expect(hayEnlace("Sistema interno")).toBe(true);
  });

  it("a un cliente no le muestra el sistema interno ni crear cuenta", () => {
    mostrarCon("cliente");

    expect(hayEnlace("Mis entradas")).toBe(true);
    expect(hayEnlace("Sistema interno")).toBe(false);
    expect(hayEnlace("Control de la puerta")).toBe(false);
    expect(hayEnlace("Crear cuenta")).toBe(false);
  });

  it.each<Rol>(["organizador", "validador"])("a un %s no le muestra mis entradas", (rol) => {
    mostrarCon(rol);

    expect(hayEnlace("Mis entradas")).toBe(false);
    expect(hayEnlace("Sistema interno")).toBe(true);
  });
});
