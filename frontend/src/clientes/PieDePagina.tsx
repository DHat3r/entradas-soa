import { Link } from "react-router-dom";
import { useSesion } from "../lib/sesion";
import { BotonTema } from "../lib/tema";

const REPOSITORIO = "https://github.com/DHat3r/entradas-soa";

/** Los enlaces dependen de la sesión, igual que la cabecera: nadie llega a una pantalla sin acceso. */
export function PieDePagina() {
  const { usuario } = useSesion();
  const esCliente = usuario?.rol === "cliente";
  const esInterno = usuario !== null && !esCliente;

  return (
    <footer className="cl-pie">
      <div className="cl-pie-interior">
        <div className="cl-pie-marca">
          <Link to="/" className="cl-marca" aria-label="Taquilla">
            <i className="logo" aria-hidden="true" />
            <span>Taquilla</span>
          </Link>
          <p>Venta de entradas hecha con servicios independientes que se comunican por RabbitMQ.</p>
        </div>
        <div className="cl-pie-columnas">
          <nav aria-label="Clientes">
            <h2>Clientes</h2>
            <ul>
              <li>
                <Link to="/" onClick={() => window.scrollTo({ top: 0 })}>
                  Eventos
                </Link>
              </li>
              {!esInterno && (
                <li>
                  <Link to="/mis-entradas">Mis entradas</Link>
                </li>
              )}
              {!usuario && (
                <li>
                  <Link to="/registro">Crear cuenta</Link>
                </li>
              )}
            </ul>
          </nav>
          {!esCliente && (
            <nav aria-label="Equipo">
              <h2>Equipo</h2>
              <ul>
                <li>
                  <Link to="/interno">Sistema interno</Link>
                </li>
                <li>
                  <Link to="/interno/puerta">Control de la puerta</Link>
                </li>
              </ul>
            </nav>
          )}
          <nav aria-label="Proyecto">
            <h2>Proyecto</h2>
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
        <div className="cl-pie-legal">
          <p>
            Proyecto de portafolio. Los pagos son simulados y, en local, los correos se capturan en
            Mailpit.
          </p>
          <BotonTema />
        </div>
      </div>
    </footer>
  );
}
