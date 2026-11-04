import { useCallback, useEffect, useState } from "react";
import { ErrorApi } from "./api";

/** Carga datos al montar la pantalla y expone los tres estados que toda pantalla debe mostrar. */
export function useCarga<T>(cargar: () => Promise<T>, dependencias: unknown[] = []) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const recargar = useCallback(cargar, dependencias);

  const ejecutar = useCallback(async () => {
    try {
      setDatos(await recargar());
      setError(null);
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "Algo salió mal. Intenta de nuevo.");
    } finally {
      setCargando(false);
    }
  }, [recargar]);

  useEffect(() => {
    void ejecutar();
  }, [ejecutar]);

  return { datos, error, cargando, recargar: ejecutar, setDatos };
}
