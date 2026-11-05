import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, Link, Navigate, Outlet, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SubirAlNavegar } from "./SubirAlNavegar";

const subir = vi.fn();

function montar() {
  const router = createMemoryRouter([
    {
      element: (
        <>
          <SubirAlNavegar />
          <Outlet />
        </>
      ),
      children: [
        {
          path: "/",
          element: (
            <>
              <Link to="/otra">Ir a otra</Link>
              <Link to="/">Ir a la misma</Link>
              <Link to="/redirige">Ir a una que redirige</Link>
            </>
          ),
        },
        { path: "/otra", element: <p>Otra</p> },
        { path: "/redirige", element: <Navigate to="/otra" replace /> },
      ],
    },
  ]);
  render(<RouterProvider router={router} />);
  return router;
}

describe("SubirAlNavegar", () => {
  beforeEach(() => {
    subir.mockClear();
    window.scrollTo = subir as unknown as typeof window.scrollTo;
  });

  afterEach(cleanup);

  it("no mueve el scroll en la carga inicial", () => {
    montar();

    expect(subir).not.toHaveBeenCalled();
  });

  it("sube al ir a otra página", () => {
    montar();

    fireEvent.click(screen.getByRole("link", { name: "Ir a otra" }));

    expect(subir).toHaveBeenCalledOnce();
    expect(subir).toHaveBeenCalledWith({ top: 0, behavior: "instant" });
  });

  it("no mueve el scroll si el enlace lleva a la misma página", () => {
    montar();

    fireEvent.click(screen.getByRole("link", { name: "Ir a la misma" }));

    expect(subir).not.toHaveBeenCalled();
  });

  it("sube cuando una ruta redirige", () => {
    montar();

    fireEvent.click(screen.getByRole("link", { name: "Ir a una que redirige" }));

    expect(screen.getByText("Otra")).toBeTruthy();
    expect(subir).toHaveBeenCalled();
  });

  it("respeta la posición al volver atrás", async () => {
    const router = montar();
    fireEvent.click(screen.getByRole("link", { name: "Ir a otra" }));
    subir.mockClear();

    await act(() => router.navigate(-1));

    expect(screen.getByRole("link", { name: "Ir a otra" })).toBeTruthy();
    expect(subir).not.toHaveBeenCalled();
  });
});
