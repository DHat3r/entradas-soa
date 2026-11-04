import { Link, Outlet, useNavigate } from "react-router-dom";
import { useSesion } from "../lib/sesion";
import "./clientes.css";
import "./portada.css";

const REPOSITORIO = "https://github.com/DHat3r/entradas-soa";

function PieDePagina() {
  return (
    <footer className="cl-pie">
      <div className="cl-pie-interior">
        <div className="cl-pie-marca">
          <Link to="/" className="cl-marca">
            <img src="/icono.svg" alt="" />
            <span>Taquilla</span>
          </Link>
          <p>Venta de entradas hecha con servicios independientes que se comunican por RabbitMQ.</p>
        </div>
        <div className="cl-pie-columnas">
          <nav aria-label="Clientes">
            <h3>Clientes</h3>
            <ul>
              <li>
                <Link to="/">Eventos</Link>
              </li>
              <li>
                <Link to="/mis-entradas">Mis entradas</Link>
              </li>
              <li>
                <Link to="/registro">Crear cuenta</Link>
              </li>
            </ul>
          </nav>
          <nav aria-label="Equipo">
            <h3>Equipo</h3>
            <ul>
              <li>
                <Link to="/interno">Sistema interno</Link>
              </li>
              <li>
                <Link to="/interno/puerta">Control de la puerta</Link>
              </li>
            </ul>
          </nav>
          <nav aria-label="Proyecto">
            <h3>Proyecto</h3>
            <ul>
              <li>
                <a href={REPOSITORIO}>Código en GitHub</a>
              </li>
              <li>
                <a href={`${REPOSITORIO}/blob/main/docs/arquitectura.md`}>Arquitectura</a>
              </li>
            </ul>
          </nav>
        </div>
        <p className="cl-pie-legal">Proyecto de portafolio. Los pagos son simulados.</p>
      </div>
    </footer>
  );
}

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
