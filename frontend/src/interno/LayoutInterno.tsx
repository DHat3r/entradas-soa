import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useSesion } from "../lib/sesion";
import "./interno.css";

export function LayoutInterno() {
  const { usuario, salir } = useSesion();
  const navegar = useNavigate();
  const esOrganizador = usuario?.rol === "organizador";

  async function cerrarSesion() {
    await salir();
    navegar("/interno/ingresar");
  }

  return (
    <div className="in-pagina">
      <aside className="in-barra">
        <Link to="/interno" className="in-marca">
          <img src="/icono.svg" alt="" />
          Taquilla Interno
        </Link>

        <nav className="in-nav" aria-label="Interno">
          {esOrganizador && (
            <NavLink to="/interno" end>
              Eventos
            </NavLink>
          )}
          {esOrganizador && <NavLink to="/interno/eventos/nuevo">Nuevo evento</NavLink>}
          <NavLink to="/interno/puerta">Puerta</NavLink>
        </nav>

        <div className="in-usuario">
          <span>{usuario?.nombre}</span>
          <button type="button" className="boton boton-borde" onClick={cerrarSesion}>
            Salir
          </button>
        </div>
      </aside>

      <main className="in-contenido">
        <Outlet />
      </main>
    </div>
  );
}
