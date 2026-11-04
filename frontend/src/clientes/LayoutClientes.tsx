import { Link, Outlet, useNavigate } from "react-router-dom";
import { useSesion } from "../lib/sesion";
import "./clientes.css";

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
        <Link to="/" className="cl-marca">
          <img src="/icono.svg" alt="" />
          Taquilla
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
            <Link to="/ingresar">Ingresar</Link>
          )}
        </nav>
      </header>
      <main className="cl-contenido">
        <Outlet />
      </main>
      <footer className="cl-pie">Proyecto de portafolio. Los pagos son simulados.</footer>
    </div>
  );
}
