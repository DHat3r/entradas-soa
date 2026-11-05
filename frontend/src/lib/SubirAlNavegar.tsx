import { useEffect, useRef } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

/** El navegador no sube solo al cambiar de ruta en una app React. Al volver atrás, respeta la posición. */
export function SubirAlNavegar() {
  const { pathname } = useLocation();
  const tipo = useNavigationType();
  const tipoActual = useRef(tipo);
  tipoActual.current = tipo;

  // Depende solo de la ruta: cambiar de tipo sin cambiar de página no debe mover el scroll.
  useEffect(() => {
    if (tipoActual.current !== "POP") window.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname]);

  return null;
}
