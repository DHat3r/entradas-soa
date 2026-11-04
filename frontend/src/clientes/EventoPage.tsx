import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ErrorApi } from "../lib/api";
import { fechaLarga, pesos } from "../lib/formato";
import { useSesion } from "../lib/sesion";
import { useCarga } from "../lib/useCarga";

const MAXIMO_POR_COMPRA = 6;

export function EventoPage() {
  const { id = "" } = useParams();
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const { datos: evento, error, cargando, recargar } = useCarga(() => api.evento(id), [id]);
  const [sectorId, setSectorId] = useState<string | null>(null);
  const [cantidad, setCantidad] = useState(1);
  const [enviando, setEnviando] = useState(false);
  const [errorCompra, setErrorCompra] = useState<string | null>(null);

  if (cargando) return <p className="cargando">Cargando evento…</p>;
  if (error || !evento) {
    return (
      <p className="aviso aviso-error" role="alert">
        {error ?? "No encontramos este evento."}
      </p>
    );
  }

  const sector = evento.sectores.find((s) => s.id === sectorId) ?? null;
  const maximo = Math.min(sector?.disponibles ?? MAXIMO_POR_COMPRA, MAXIMO_POR_COMPRA);
  const cantidadValida = Math.min(cantidad, Math.max(maximo, 1));
  const agotado = evento.sectores.every((s) => s.disponibles === 0);
  const esInterno = usuario !== null && usuario.rol !== "cliente";

  async function reservar(formulario: FormEvent) {
    formulario.preventDefault();
    if (!sector) return;
    if (!usuario) {
      navegar(`/ingresar?volver=${encodeURIComponent(`/eventos/${id}`)}`);
      return;
    }
    setEnviando(true);
    setErrorCompra(null);
    try {
      const reserva = await api.reservar(sector.id, cantidadValida);
      navegar(`/reservas/${reserva.id}`);
    } catch (e) {
      setErrorCompra(e instanceof ErrorApi ? e.message : "No pudimos reservar. Intenta de nuevo.");
      // Otra persona pudo llevarse los cupos: se actualizan los disponibles.
      await recargar();
      setEnviando(false);
    }
  }

  return (
    <article className="detalle">
      <div>
        <h1>{evento.nombre}</h1>
        <p className="detalle-datos">
          <span>{fechaLarga(evento.fecha)}</span>
          <span>{evento.lugar}</span>
        </p>
        {evento.descripcion && <p className="detalle-descripcion">{evento.descripcion}</p>}
      </div>

      <form className="compra" onSubmit={reservar}>
        <h2>Elige tus entradas</h2>
        <fieldset className="opciones-sector">
          <legend className="sr-oculto">Sector</legend>
          {evento.sectores.map((s) => (
            <label key={s.id} className="opcion-sector">
              <input
                type="radio"
                name="sector"
                value={s.id}
                checked={sectorId === s.id}
                disabled={s.disponibles === 0}
                onChange={() => setSectorId(s.id)}
              />
              <span>
                {s.nombre}
                <small>{s.disponibles === 0 ? "Agotado" : `${s.disponibles} disponibles`}</small>
              </span>
              <strong>{pesos(s.precio_clp)}</strong>
            </label>
          ))}
        </fieldset>

        <label className="campo">
          Cantidad
          <select
            value={cantidadValida}
            onChange={(e) => setCantidad(Number(e.target.value))}
            disabled={!sector}
          >
            {Array.from({ length: Math.max(maximo, 1) }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <p className="total">
          <span>Total</span>
          <strong>{pesos((sector?.precio_clp ?? 0) * cantidadValida)}</strong>
        </p>

        {errorCompra && (
          <p className="aviso aviso-error" role="alert">
            {errorCompra}
          </p>
        )}
        {esInterno && (
          <p className="aviso aviso-info">
            Estás en una cuenta interna. Para comprar, ingresa con una cuenta de cliente.
          </p>
        )}

        <button
          className="boton boton-acento boton-ancho"
          disabled={!sector || enviando || agotado || esInterno}
        >
          {agotado ? "Agotado" : enviando ? "Reservando…" : "Reservar"}
        </button>
        <small className="nota">Tus entradas quedan apartadas por 10 minutos para que pagues.</small>
      </form>
    </article>
  );
}
