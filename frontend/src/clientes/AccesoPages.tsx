import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { api, ErrorApi } from "../lib/api";
import { rutaSegura, useSesion } from "../lib/sesion";

function useEnvio() {
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(accion: () => Promise<void>) {
    setEnviando(true);
    setError(null);
    try {
      await accion();
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "Algo salió mal. Intenta de nuevo.");
      setEnviando(false);
    }
  }

  return { error, enviando, enviar };
}

export function IngresarPage() {
  const [parametros] = useSearchParams();
  const destino = rutaSegura(parametros.get("volver"), "/");
  const { usuario, refrescar } = useSesion();
  const navegar = useNavigate();
  const { error, enviando, enviar } = useEnvio();
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");

  if (usuario) return <Navigate to={destino} replace />;

  function alEnviar(formulario: FormEvent) {
    formulario.preventDefault();
    void enviar(async () => {
      await api.ingresar(correo, password);
      await refrescar();
      navegar(destino, { replace: true });
    });
  }

  return (
    <section className="acceso">
      <h1>Ingresar</h1>
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
      <p className="acceso-cambio">
        ¿No tienes cuenta?{" "}
        <Link to={`/registro?volver=${encodeURIComponent(destino)}`}>Crea una</Link>
      </p>
    </section>
  );
}

export function RegistroPage() {
  const [parametros] = useSearchParams();
  const destino = rutaSegura(parametros.get("volver"), "/");
  const { usuario, refrescar } = useSesion();
  const navegar = useNavigate();
  const { error, enviando, enviar } = useEnvio();
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");

  if (usuario) return <Navigate to={destino} replace />;

  function alEnviar(formulario: FormEvent) {
    formulario.preventDefault();
    void enviar(async () => {
      await api.registrar(nombre, correo, password);
      await api.ingresar(correo, password);
      await refrescar();
      navegar(destino, { replace: true });
    });
  }

  return (
    <section className="acceso">
      <h1>Crear cuenta</h1>
      <form className="formulario" onSubmit={alEnviar}>
        <label className="campo">
          Nombre
          <input
            autoComplete="name"
            required
            minLength={2}
            maxLength={120}
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        </label>
        <label className="campo">
          Correo
          <input
            type="email"
            autoComplete="email"
            required
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
          />
          <small>Aquí te enviaremos tus entradas.</small>
        </label>
        <label className="campo">
          Contraseña
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <small>Al menos 8 caracteres.</small>
        </label>
        {error && (
          <p className="aviso aviso-error" role="alert">
            {error}
          </p>
        )}
        <button className="boton boton-acento boton-ancho" disabled={enviando}>
          {enviando ? "Creando…" : "Crear cuenta"}
        </button>
      </form>
      <p className="acceso-cambio">
        ¿Ya tienes cuenta? <Link to={`/ingresar?volver=${encodeURIComponent(destino)}`}>Ingresa</Link>
      </p>
    </section>
  );
}
