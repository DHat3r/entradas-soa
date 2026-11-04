import { Route, Routes } from "react-router-dom";
import { RequiereRol } from "../lib/sesion";

/** El sistema interno se implementa en el siguiente paso. */
export function RutasInternas() {
  return (
    <RequiereRol roles={["organizador", "validador"]} ingreso="/ingresar">
      <Routes>
        <Route index element={<p className="vacio">Sistema interno en construcción.</p>} />
      </Routes>
    </RequiereRol>
  );
}
