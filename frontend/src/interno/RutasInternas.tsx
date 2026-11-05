import { Navigate, Route, Routes } from "react-router-dom";
import { RequiereRol, useSesion } from "../lib/sesion";
import { EventosInternoPage } from "./EventosInternoPage";
import { IngresarInternoPage } from "./IngresarInternoPage";
import { LayoutInterno } from "./LayoutInterno";
import { NuevoEventoPage } from "./NuevoEventoPage";
import { PuertaPage } from "./PuertaPage";

/** El organizador ve sus eventos; el validador va directo a la puerta. */
function InicioInterno() {
  const { usuario } = useSesion();
  if (usuario?.rol === "validador") return <Navigate to="/interno/puerta" replace />;
  return <EventosInternoPage />;
}

/** Rutas relativas a /interno/*, porque App.tsx monta este componente ahí. */
export function RutasInternas() {
  return (
    <Routes>
      <Route path="ingresar" element={<IngresarInternoPage />} />
      <Route
        element={
          // El div da el fondo del tema también al aviso de acceso denegado que RequiereRol muestra sin barra.
          <div className="in-pagina in-envoltura">
            <RequiereRol roles={["organizador", "validador"]} ingreso="/interno/ingresar">
              <LayoutInterno />
            </RequiereRol>
          </div>
        }
      >
        <Route index element={<InicioInterno />} />
        <Route
          path="eventos/nuevo"
          element={
            <RequiereRol roles={["organizador"]} ingreso="/interno/ingresar">
              <NuevoEventoPage />
            </RequiereRol>
          }
        />
        <Route path="puerta" element={<PuertaPage />} />
        <Route path="*" element={<p className="vacio">No encontramos esta página.</p>} />
      </Route>
    </Routes>
  );
}
