import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ErrorApi } from "../lib/api";
import { aDatosDeEvento, type FormularioEvento, type FormularioSector } from "./formularioEvento";

const MAXIMO_SECTORES = 10;

const SECTOR_VACIO: FormularioSector = { nombre: "", precio: "", capacidad: "" };

const FORMULARIO_VACIO: FormularioEvento = {
  nombre: "",
  lugar: "",
  fecha: "",
  descripcion: "",
  sectores: [SECTOR_VACIO],
};

/** Fecha y hora actuales con el formato que espera datetime-local (zona local). */
function ahoraLocal(): string {
  const ahora = new Date();
  ahora.setMinutes(ahora.getMinutes() - ahora.getTimezoneOffset());
  return ahora.toISOString().slice(0, 16);
}

export function NuevoEventoPage() {
  const navegar = useNavigate();
  const [formulario, setFormulario] = useState<FormularioEvento>(FORMULARIO_VACIO);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const minimoFecha = ahoraLocal();

  function cambiarCampo(campo: "nombre" | "lugar" | "fecha" | "descripcion", valor: string) {
    setFormulario((actual) => ({ ...actual, [campo]: valor }));
  }

  function cambiarSector(indice: number, campo: keyof FormularioSector, valor: string) {
    setFormulario((actual) => ({
      ...actual,
      sectores: actual.sectores.map((sector, i) =>
        i === indice ? { ...sector, [campo]: valor } : sector,
      ),
    }));
  }

  function agregarSector() {
    setFormulario((actual) => ({
      ...actual,
      sectores: [...actual.sectores, { ...SECTOR_VACIO }],
    }));
  }

  function quitarSector(indice: number) {
    setFormulario((actual) => ({
      ...actual,
      sectores: actual.sectores.filter((_, i) => i !== indice),
    }));
  }

  async function alEnviar(evento: FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await api.crearEvento(aDatosDeEvento(formulario));
      navegar("/interno");
    } catch (e) {
      setError(e instanceof ErrorApi ? e.message : "No pudimos crear el evento. Intenta de nuevo.");
      setEnviando(false);
    }
  }

  return (
    <section>
      <header className="in-encabezado">
        <h1>Nuevo evento</h1>
      </header>

      <form className="formulario in-tarjeta" onSubmit={alEnviar}>
        <p className="in-ayuda">
          El evento queda en borrador. Podrás publicarlo desde la lista de eventos cuando esté listo
          para el público.
        </p>

        <label className="campo">
          Nombre
          <input
            required
            maxLength={160}
            value={formulario.nombre}
            onChange={(e) => cambiarCampo("nombre", e.target.value)}
          />
        </label>

        <label className="campo">
          Lugar
          <input
            required
            maxLength={160}
            value={formulario.lugar}
            onChange={(e) => cambiarCampo("lugar", e.target.value)}
          />
        </label>

        <label className="campo">
          Fecha y hora
          <input
            type="datetime-local"
            required
            min={minimoFecha}
            value={formulario.fecha}
            onChange={(e) => cambiarCampo("fecha", e.target.value)}
          />
        </label>

        <label className="campo">
          Descripción
          <textarea
            rows={4}
            maxLength={2000}
            value={formulario.descripcion}
            onChange={(e) => cambiarCampo("descripcion", e.target.value)}
          />
        </label>

        <fieldset className="in-sectores">
          <legend>Sectores</legend>
          {formulario.sectores.map((sector, indice) => (
            <fieldset key={indice} className="in-sector">
              <legend>Sector {indice + 1}</legend>
              <div className="in-sector-campos">
                <label className="campo">
                  Nombre
                  <input
                    required
                    value={sector.nombre}
                    onChange={(e) => cambiarSector(indice, "nombre", e.target.value)}
                  />
                </label>
                <label className="campo">
                  Precio (CLP)
                  <input
                    type="number"
                    inputMode="numeric"
                    required
                    min={0}
                    step={1}
                    value={sector.precio}
                    onChange={(e) => cambiarSector(indice, "precio", e.target.value)}
                  />
                </label>
                <label className="campo">
                  Capacidad
                  <input
                    type="number"
                    inputMode="numeric"
                    required
                    min={1}
                    max={100000}
                    step={1}
                    value={sector.capacidad}
                    onChange={(e) => cambiarSector(indice, "capacidad", e.target.value)}
                  />
                </label>
              </div>
              <button
                type="button"
                className="boton boton-borde"
                onClick={() => quitarSector(indice)}
                disabled={formulario.sectores.length === 1}
              >
                Quitar
              </button>
            </fieldset>
          ))}
          <button
            type="button"
            className="boton boton-borde"
            onClick={agregarSector}
            disabled={formulario.sectores.length >= MAXIMO_SECTORES}
          >
            Agregar sector
          </button>
          <small className="in-ayuda">
            Entre 1 y {MAXIMO_SECTORES} sectores. Siempre debe quedar al menos uno.
          </small>
        </fieldset>

        {error && (
          <p className="aviso aviso-error" role="alert">
            {error}
          </p>
        )}

        <button className="boton boton-acento boton-ancho" disabled={enviando}>
          {enviando ? "Creando…" : "Crear evento"}
        </button>
      </form>
    </section>
  );
}
