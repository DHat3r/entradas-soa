import { Link } from "react-router-dom";
import { api, type Evento } from "../lib/api";
import { diaYMes, pesos, precioDesde } from "../lib/formato";
import { useCarga } from "../lib/useCarga";

function TarjetaEvento({ evento }: { evento: Evento }) {
  const { dia, mes } = diaYMes(evento.fecha);
  const agotado = evento.sectores.every((sector) => sector.disponibles === 0);
  const desde = precioDesde(evento.sectores.map((sector) => sector.precio_clp));

  return (
    <li>
      <Link to={`/eventos/${evento.id}`} className="boleto">
        <div className="boleto-fecha">
          <span className="boleto-dia">{dia}</span>
          <span className="boleto-mes">{mes}</span>
        </div>
        <div className="boleto-cuerpo">
          <h3>{evento.nombre}</h3>
          <p className="boleto-lugar">{evento.lugar}</p>
          <p className="boleto-precio">
            {agotado ? (
              <strong>Agotado</strong>
            ) : (
              <>
                Desde <strong>{pesos(desde)}</strong>
              </>
            )}
          </p>
        </div>
      </Link>
    </li>
  );
}

export function EventosPage() {
  const { datos: eventos, error, cargando } = useCarga(api.eventos);

  return (
    <>
      <section className="portada">
        <h1>
          Tu próxima salida, <em>asegurada.</em>
        </h1>
        <p>Elige tu sector, paga en un paso y recibe tus entradas con QR en tu correo.</p>
      </section>

      <h2 className="seccion-titulo">Próximos eventos</h2>
      {cargando && <p className="cargando">Cargando eventos…</p>}
      {error && (
        <p className="aviso aviso-error" role="alert">
          {error}
        </p>
      )}
      {eventos?.length === 0 && (
        <p className="vacio">Todavía no hay eventos a la venta. Vuelve pronto.</p>
      )}
      {eventos && eventos.length > 0 && (
        <ul className="tarjetas">
          {eventos.map((evento) => (
            <TarjetaEvento key={evento.id} evento={evento} />
          ))}
        </ul>
      )}
    </>
  );
}
