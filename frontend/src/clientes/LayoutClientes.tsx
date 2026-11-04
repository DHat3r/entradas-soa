import { Link, Outlet, useNavigate } from "react-router-dom";
import { useSesion } from "../lib/sesion";
import "./clientes.css";
import { PieDePagina } from "./PieDePagina";
import "./portada.css";

export function LayoutClientes() {
  const { usuario, salir } = useSesion();
  const navegar = useNavigate();

  async function cerrarSesion() {
    await salir();
    navegar("/");
  }

  return (
    <div className="cl-pagina">
      <header className="cl-cabecera">
        {/* Ya estando en la portada, la ruta no cambia: por eso el logo sube por su cuenta. */}
        <Link
          to="/"
          className="cl-marca"
          aria-label="Taquilla, ir al inicio"
          onClick={() => window.scrollTo({ top: 0 })}
        >
          <img src="/icono.svg" alt="" />
          <span>Taquilla</span>
        </Link>
        <nav className="cl-nav" aria-label="Principal">
          {usuario ? (
            <>
              {usuario.rol === "cliente" ? (
                <Link to="/mis-entradas">Mis entradas</Link>
              ) : (
                <Link to="/interno">Sistema interno</Link>
              )}
              <button type="button" onClick={cerrarSesion}>
                Salir
              </button>
            </>
          ) : (
            <>
              <Link to="/ingresar">Ingresar</Link>
              <Link to="/registro" className="boton boton-acento">
                Crear cuenta
              </Link>
            </>
          )}
        </nav>
      </header>
      <main className="cl-contenido">
        <Outlet />
      </main>
      <PieDePagina />
    </div>
  );
}
