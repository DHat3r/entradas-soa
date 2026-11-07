import { afterEach, describe, expect, it, vi } from "vitest";
import html from "../../index.html?raw";

// Prueba el script real de index.html, no una copia: es lo que corre antes de pintar.
const script = /<script>([\s\S]*?)<\/script>/.exec(html)![1];

function ejecutar({
  guardado = null,
  sistemaClaro = false,
  bloqueado = false,
  sinMatchMedia = false,
}: {
  guardado?: string | null;
  sistemaClaro?: boolean;
  bloqueado?: boolean;
  sinMatchMedia?: boolean;
}) {
  delete document.documentElement.dataset.tema;
  document.head.innerHTML = '<meta name="theme-color" content="#17122a" />';
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    if (bloqueado) throw new Error("Almacenamiento bloqueado");
    return guardado;
  });
  vi.stubGlobal(
    "matchMedia",
    sinMatchMedia ? undefined : vi.fn(() => ({ matches: sistemaClaro })),
  );
  new Function(script)();
  return {
    tema: document.documentElement.dataset.tema,
    color: document.querySelector('meta[name="theme-color"]')?.getAttribute("content"),
  };
}

describe("script de tema de index.html", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("sigue al sistema la primera vez", () => {
    expect(ejecutar({ sistemaClaro: true })).toEqual({ tema: "claro", color: "#f4eadd" });
    expect(ejecutar({ sistemaClaro: false })).toEqual({ tema: "oscuro", color: "#17122a" });
  });

  it("la elección guardada manda sobre el sistema", () => {
    expect(ejecutar({ guardado: "oscuro", sistemaClaro: true }).tema).toBe("oscuro");
    expect(ejecutar({ guardado: "claro", sistemaClaro: false }).tema).toBe("claro");
  });

  it("ignora un valor guardado inválido y sigue al sistema", () => {
    expect(ejecutar({ guardado: "azul", sistemaClaro: true }).tema).toBe("claro");
  });

  it("sigue al sistema si el almacenamiento está bloqueado", () => {
    expect(ejecutar({ bloqueado: true, sistemaClaro: true }).tema).toBe("claro");
  });

  it("usa oscuro si el navegador no tiene matchMedia", () => {
    expect(ejecutar({ sinMatchMedia: true }).tema).toBe("oscuro");
  });
});
