import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api, ErrorApi, type Rol } from "../lib/api";
import { rutaSegura, useSesion } from "../lib/sesion";

const MENSAJE_SIN_ACCESO = "Esta cuenta no tiene acceso al sistema interno";

/** Pantalla de inicio de cada rol interno. */
function inicioPara(rol: Rol): string {
  return rol === "organizador" ? "/interno" : "/interno/puerta";
}

export function IngresarInternoPage() {
  const [parametros] = useSearchParams();
  const { usuario, cargando, refrescar, salir } = useSesion();
  const navegar = useNavigate();
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (cargando) return <p className="cargando">Cargando…</p>;
  if (usuario && usuario.rol !== "cliente") {
    return <Navigate to={rutaSegura(parametros.get("volver"), inicioPara(usuario.rol))} replace />;
  }

  async function alEnviar(formulario: FormEvent) {
    formulario.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await api.ingresar(correo, password);
      const actual = await refrescar();
      if (!actual) {
        setError("No pudimos iniciar sesión. Intenta de nuevo.");
        return;
      }
      if (actual.rol === "cliente") {
        await salir();
        setError(MENSAJE_SIN_ACCESO);
        return;
      }
      navegar(rutaSegura(parametros.get("volver"), inicioPara(actual.rol)), { replace: true });
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "Algo salió mal. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="in-pagina in-centrado">
      <section className="in-tarjeta in-acceso">
        <h1>Taquilla Interno</h1>
        <p className="in-ayuda">Ingresa con tu cuenta de organizador o validador.</p>
        <form className="formulario" onSubmit={alEnviar}>
          <label className="campo">
            Correo
            <input
              type="email"
              autoComplete="email"
              required
              value={correo}
              onChange={(e) => setCorreo(e.target.value)}
            />
          </label>
          <label className="campo">
            Contraseña
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && (
            <p className="aviso aviso-error" role="alert">
              {error}
            </p>
          )}
          <button className="boton boton-acento boton-ancho" disabled={enviando}>
            {enviando ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
      </section>
    </div>
  );
}
