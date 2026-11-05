import { Link } from "react-router-dom";
import { api, type Evento } from "../lib/api";
import { diaYMes, pesos, precioDesde } from "../lib/formato";
import { useSesion } from "../lib/sesion";
import { useCarga } from "../lib/useCarga";

const DATOS = [
  { titulo: "10 minutos", detalle: "con tus cupos apartados" },
  { titulo: "1 solo uso", detalle: "por cada QR en la puerta" },
  { titulo: "Hasta 6", detalle: "entradas por compra" },
  { titulo: "Pago simulado", detalle: "sin datos de tarjeta" },
];

const VENTAJAS = [
  {
    titulo: "Cupos apartados",
    texto: "Al reservar, tus cupos quedan guardados 10 minutos. Si no pagas, vuelven a la venta.",
    trazo: "M12 7v5l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z",
  },
  {
    titulo: "Entradas con QR",
    texto: "Las recibes por correo y también las encuentras en tu cuenta, listas para mostrar.",
    trazo: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2v2h-2zM18 18h2v2h-2zM14 18h2v2h-2zM18 14h2v2h-2z",
  },
  {
    titulo: "Control en la puerta",
    texto: "Cada código está firmado y entra una sola vez, aunque lo escaneen en dos accesos.",
    trazo: "M12 3 4 6v6c0 4.5 3.2 7.8 8 9 4.8-1.2 8-4.5 8-9V6zM9 12l2 2 4-4",
  },
];

const PASOS = [
  "Elige tu sector y hasta 6 entradas, e ingresa con tu cuenta",
  "Paga dentro de los 10 minutos que dura la reserva",
  "Recibe un QR por entrada en tu correo",
];

/** Dibujo de un QR para la ilustración. No es un código real ni se puede escanear. */
function DibujoDeQr() {
  const lado = 21;
  const celdas: [number, number][] = [];
  for (let y = 0; y < lado; y++) {
    for (let x = 0; x < lado; x++) {
      const enEsquina = (x < 8 && y < 8) || (x > 12 && y < 8) || (x < 8 && y > 12);
      if (!enEsquina && (x * 7 + y * 13 + x * y) % 3 === 0) celdas.push([x, y]);
    }
  }
  const esquinas = [
    [0, 0],
    [14, 0],
    [0, 14],
  ];
  return (
    <svg className="muestra-qr" viewBox={`0 0 ${lado} ${lado}`} aria-hidden="true">
      <g fill="#06110d">
        {celdas.map(([x, y]) => (
          <rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" />
        ))}
        {esquinas.map(([x, y]) => (
          <g key={`${x}-${y}`}>
            <path
              fillRule="evenodd"
              d={`M${x} ${y}h7v7h-7zM${x + 1} ${y + 1}v5h5v-5z`}
            />
            <rect x={x + 2} y={y + 2} width="3" height="3" />
          </g>
        ))}
      </g>
    </svg>
  );
}

function EntradaDeMuestra() {
  return (
    <div className="muestra" aria-hidden="true">
      <p className="muestra-rotulo">Así se ve tu entrada</p>
      <p className="muestra-titulo">Tu próximo evento</p>
      <p className="muestra-detalle">Sector General · Entrada 1</p>
      <DibujoDeQr />
      <div className="muestra-sello">
        <i>✓</i>
        <div>
          <small>En la puerta</small>
          <strong>Puede entrar</strong>
        </div>
      </div>
    </div>
  );
}

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
  const { usuario } = useSesion();
  const { datos: eventos, error, cargando } = useCarga(api.eventos);

  return (
    <>
      <section className="hero">
        <div>
          <p className="hero-pastilla">Proyecto de portafolio</p>
          <h1>
            Tu próxima
            <br />
            salida,
            <br />
            <span className="hero-bloque">asegurada.</span>
          </h1>
          <p className="hero-texto">
            Elige tu sector, paga en un paso y recibe tus entradas con QR en tu correo.
          </p>
          <div className="acciones">
            <a href="#eventos" className="boton boton-acento">
              Ver eventos
            </a>
            <a href="#como-funciona" className="boton">
              Cómo funciona
            </a>
          </div>
        </div>
        <EntradaDeMuestra />
      </section>

      <ul className="franja">
        {DATOS.map((dato) => (
          <li key={dato.titulo}>
            <strong>{dato.titulo}</strong>
            <span>{dato.detalle}</span>
          </li>
        ))}
      </ul>

      <section id="eventos" className="seccion">
        <div className="seccion-cabeza">
          <h2>
            Próximos <span className="destacado">eventos</span>
          </h2>
          <p>Elige uno y mira los sectores, los precios y los cupos que quedan.</p>
        </div>
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
      </section>

      <section id="como-funciona" className="seccion">
        <div className="seccion-cabeza">
          <h2>
            Pensado para <span className="destacado">no perderte</span> nada
          </h2>
          <p>Desde que reservas hasta que entras al evento.</p>
        </div>
        <ul className="ventajas">
          {VENTAJAS.map((ventaja) => (
            <li key={ventaja.titulo}>
              <article className="ventaja">
                <div className="ventaja-icono">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d={ventaja.trazo} />
                  </svg>
                </div>
                <h3>{ventaja.titulo}</h3>
                <p>{ventaja.texto}</p>
              </article>
            </li>
          ))}
        </ul>
      </section>

      <section className="seccion">
        <div className="bloque">
          <div>
            <h2>
              Compra en <span className="destacado">tres pasos</span>
            </h2>
            <p className="bloque-texto">
              Si quedan cupos, son tuyos mientras pagas. Si el pago falla o se acaba el plazo, se liberan solos.
            </p>
            <ul className="lista-chequeo">
              {PASOS.map((paso) => (
                <li key={paso}>{paso}</li>
              ))}
            </ul>
          </div>
          <div className="reserva-muestra" aria-hidden="true">
            <p className="muestra-rotulo">Ejemplo de reserva</p>
            <dl>
              <dt>Sector</dt>
              <dd>General</dd>
              <dt>Entradas</dt>
              <dd>2</dd>
              <dt>Tiempo restante</dt>
              <dd>9:41</dd>
            </dl>
            <p className="reserva-muestra-total">
              <span>Total</span>
              <strong>{pesos(30000)}</strong>
            </p>
          </div>
        </div>
      </section>

      <section className="llamada">
        <h2>
          ¿Listo para
          <br />
          <span className="destacado">tu próxima salida?</span>
        </h2>
        <p>Crea tu cuenta y ten tus entradas siempre a mano, en tu correo y en tu teléfono.</p>
        <div className="acciones">
          <a href="#eventos" className="boton boton-acento">
            Ver eventos
          </a>
          {!usuario && (
            <Link to="/registro" className="boton">
              Crear cuenta
            </Link>
          )}
        </div>
      </section>
    </>
  );
}
