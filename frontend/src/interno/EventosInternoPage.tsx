import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ErrorApi, type Evento, type Sector } from "../lib/api";
import { fechaLarga, pesos } from "../lib/formato";
import { useCarga } from "../lib/useCarga";

/** Suma lo vendido y los ingresos potenciales (incluye cupos apartados aún no pagados). */
function totalesDe(sectores: Sector[]) {
  return sectores.reduce(
    (acumulado, sector) => ({
      vendidas: acumulado.vendidas + sector.vendidos,
      ingresos: acumulado.ingresos + sector.precio_clp * sector.vendidos,
    }),
    { vendidas: 0, ingresos: 0 },
  );
}

export function EventosInternoPage() {
  const { datos: eventos, error, cargando, recargar } = useCarga(() => api.misEventos());
  const [publicando, setPublicando] = useState<string | null>(null);
  const [errorPublicar, setErrorPublicar] = useState<string | null>(null);

  async function publicar(evento: Evento) {
    // Publicar deja el evento visible al público y no hay forma de despublicarlo desde aquí.
    const confirmado = window.confirm(
      `¿Publicar "${evento.nombre}"? Quedará visible para el público y no se puede volver a ocultar.`,
    );
    if (!confirmado) return;

    setPublicando(evento.id);
    setErrorPublicar(null);
    try {
      await api.publicarEvento(evento.id);
      await recargar();
    } catch (e) {
      setErrorPublicar(
        e instanceof ErrorApi ? e.message : "No pudimos publicar el evento. Intenta de nuevo.",
      );
    } finally {
      setPublicando(null);
    }
  }

  return (
    <section>
      <header className="in-encabezado">
        <h1>Eventos</h1>
        <Link className="boton boton-acento" to="/interno/eventos/nuevo">
          Nuevo evento
        </Link>
      </header>

      {cargando && <p className="cargando">Cargando eventos…</p>}
      {error && (
        <p className="aviso aviso-error" role="alert">
          {error}
        </p>
      )}
      {errorPublicar && (
        <p className="aviso aviso-error" role="alert">
          {errorPublicar}
        </p>
      )}
      {eventos && eventos.length === 0 && (
        <p className="vacio">Aún no tienes eventos. Crea el primero con “Nuevo evento”.</p>
      )}

      {eventos && eventos.length > 0 && (
        <div className="in-lista">
          {eventos.map((evento) => {
            const publicado = evento.estado === "PUBLICADO";
            const totales = totalesDe(evento.sectores);
            return (
              <article key={evento.id} className="in-tarjeta">
                <div className="in-evento-cabecera">
                  <div>
                    <h2>{evento.nombre}</h2>
                    <p className="in-datos">
                      {fechaLarga(evento.fecha)} · {evento.lugar}
                    </p>
                  </div>
                  <span
                    className={`etiqueta ${publicado ? "in-etiqueta-publicado" : "in-etiqueta-borrador"}`}
                  >
                    {publicado ? "Publicado" : "Borrador"}
                  </span>
                </div>

                <div className="in-tabla-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Sector</th>
                        <th scope="col">Precio</th>
                        <th scope="col">Apartadas o vendidas</th>
                        <th scope="col">Disponibles</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evento.sectores.map((sector) => (
                        <tr key={sector.id}>
                          <th scope="row">{sector.nombre}</th>
                          <td>{pesos(sector.precio_clp)}</td>
                          <td>{sector.vendidos}</td>
                          <td>{sector.disponibles}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <th scope="row">Total</th>
                        <td>
                          <span className="in-rotulo">Ingresos potenciales</span>
                          {pesos(totales.ingresos)}
                        </td>
                        <td>{totales.vendidas}</td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

                <div className="in-acciones">
                  {publicado ? (
                    <Link className="boton boton-borde" to={`/eventos/${evento.id}`}>
                      Ver como cliente
                    </Link>
                  ) : (
                    <button
                      type="button"
                      className="boton boton-acento"
                      onClick={() => publicar(evento)}
                      disabled={publicando === evento.id}
                    >
                      {publicando === evento.id ? "Publicando…" : "Publicar"}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
