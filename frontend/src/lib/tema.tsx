import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export type Tema = "oscuro" | "claro";

const CLAVE = "tema";
const COLOR_DE_NAVEGADOR: Record<Tema, string> = { oscuro: "#17122a", claro: "#f4eadd" };

interface ContextoDeTema {
  tema: Tema;
  alternar: () => void;
}

const Contexto = createContext<ContextoDeTema | null>(null);

/**
 * El script de index.html ya eligió el tema antes de pintar, para evitar un parpadeo.
 * Aquí solo se lee lo que dejó en el documento.
 */
function temaDelDocumento(): Tema {
  return document.documentElement.dataset.tema === "claro" ? "claro" : "oscuro";
}

export function ProveedorDeTema({ children }: { children: ReactNode }) {
  const [tema, setTema] = useState<Tema>(temaDelDocumento);

  const alternar = useCallback(() => {
    const nuevo: Tema = temaDelDocumento() === "claro" ? "oscuro" : "claro";
    document.documentElement.dataset.tema = nuevo;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", COLOR_DE_NAVEGADOR[nuevo]);
    try {
      localStorage.setItem(CLAVE, nuevo);
    } catch {
      // Sin almacenamiento (ventana privada, por ejemplo) el tema dura hasta recargar.
    }
    setTema(nuevo);
  }, []);

  return <Contexto.Provider value={{ tema, alternar }}>{children}</Contexto.Provider>;
}

export function useTema(): ContextoDeTema {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("useTema debe usarse dentro de ProveedorDeTema");
  return contexto;
}

export function BotonTema() {
  const { tema, alternar } = useTema();
  const siguiente = tema === "oscuro" ? "claro" : "oscuro";

  return (
    <button
      type="button"
      className="boton-tema"
      onClick={alternar}
      aria-label={`Cambiar a modo ${siguiente}`}
      title={`Cambiar a modo ${siguiente}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        {tema === "oscuro" ? (
          <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
        ) : (
          <path d="M21 13.5A8.5 8.5 0 1 1 10.5 3a7 7 0 0 0 10.5 10.5Z" />
        )}
      </svg>
    </button>
  );
}
