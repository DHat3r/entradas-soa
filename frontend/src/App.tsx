import { BrowserRouter, Route, Routes } from "react-router-dom";
import { IngresarPage, RegistroPage } from "./clientes/AccesoPages";
import { CompraPage } from "./clientes/CompraPage";
import { EventoPage } from "./clientes/EventoPage";
import { EventosPage } from "./clientes/EventosPage";
import { LayoutClientes } from "./clientes/LayoutClientes";
import { MisEntradasPage } from "./clientes/MisEntradasPage";
import { RutasInternas } from "./interno/RutasInternas";
import { ProveedorDeSesion, RequiereRol } from "./lib/sesion";

function SoloCliente({ children }: { children: React.ReactNode }) {
  return (
    <RequiereRol roles={["cliente"]} ingreso="/ingresar">
      {children}
    </RequiereRol>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <ProveedorDeSesion>
        <Routes>
          <Route path="/interno/*" element={<RutasInternas />} />
          <Route element={<LayoutClientes />}>
            <Route index element={<EventosPage />} />
            <Route path="eventos/:id" element={<EventoPage />} />
            <Route path="ingresar" element={<IngresarPage />} />
            <Route path="registro" element={<RegistroPage />} />
            <Route
              path="reservas/:id"
              element={
                <SoloCliente>
                  <CompraPage />
                </SoloCliente>
              }
            />
            <Route
              path="mis-entradas"
              element={
                <SoloCliente>
                  <MisEntradasPage />
                </SoloCliente>
              }
            />
            <Route path="*" element={<p className="vacio">No encontramos esta página.</p>} />
          </Route>
        </Routes>
      </ProveedorDeSesion>
    </BrowserRouter>
  );
}
