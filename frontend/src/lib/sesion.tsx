import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { api, type Rol, type Usuario } from "./api";

interface Sesion {
  usuario: Usuario | null;
  cargando: boolean;
  /** Vuelve a preguntar quién es el usuario, por ejemplo después de ingresar. */
  refrescar: () => Promise<Usuario | null>;
  salir: () => Promise<void>;
}

const Contexto = createContext<Sesion | null>(null);

export function ProveedorDeSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  const refrescar = useCallback(async () => {
    const actual = await api.yo().catch(() => null);
    setUsuario(actual);
    return actual;
  }, []);

  useEffect(() => {
    refrescar().finally(() => setCargando(false));
  }, [refrescar]);

  const salir = useCallback(async () => {
    await api.salir();
    setUsuario(null);
  }, []);

  return (
    <Contexto.Provider value={{ usuario, cargando, refrescar, salir }}>{children}</Contexto.Provider>
  );
}

export function useSesion(): Sesion {
  const sesion = useContext(Contexto);
  if (!sesion) throw new Error("useSesion debe usarse dentro de ProveedorDeSesion");
  return sesion;
}

/**
 * Solo decide qué pantalla mostrar: la seguridad real está en los servicios, que revisan
 * el rol en cada acción. Por eso el rol viene de la API y no de algo guardado en el navegador.
 */
export function RequiereRol({
  roles,
  ingreso,
  children,
}: {
  roles: Rol[];
  ingreso: string;
  children: ReactNode;
}) {
  const { usuario, cargando } = useSesion();
  const ubicacion = useLocation();

  if (cargando) return <p className="cargando">Cargando…</p>;
  if (!usuario) {
    const volver = encodeURIComponent(ubicacion.pathname);
    return <Navigate to={`${ingreso}?volver=${volver}`} replace />;
  }
  if (!roles.includes(usuario.rol)) {
    return (
      <div className="aviso aviso-error" role="alert">
        Tu cuenta no tiene acceso a esta sección. <Link to="/">Volver al inicio</Link>
      </div>
    );
  }
  return <>{children}</>;
}

/** Evita redirecciones a otros sitios: solo se aceptan rutas internas. */
export function rutaSegura(volver: string | null, porDefecto: string): string {
  if (!volver?.startsWith("/")) return porDefecto;
  // Se interpreta igual que el navegador, porque este ignora tabulaciones y trata "\\" como "/".
  const url = new URL(volver, window.location.origin);
  return url.origin === window.location.origin ? url.pathname + url.search + url.hash : porDefecto;
}
