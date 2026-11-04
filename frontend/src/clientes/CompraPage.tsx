import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ErrorApi, type Reserva } from "../lib/api";
import { cuentaRegresiva, pesos } from "../lib/formato";
import { useCarga } from "../lib/useCarga";

const INTERVALO_CONSULTA_MS = 1000;

function usarSegundero(activo: boolean): number {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    if (!activo) return;
    const intervalo = setInterval(() => setAhora(Date.now()), 1000);
    return () => clearInterval(intervalo);
  }, [activo]);
  return ahora;
}

function Resumen({ reserva, children }: { reserva: Reserva; children?: React.ReactNode }) {
  return (
    <div className="resumen-compra">
      <dl>
        <dt>Evento</dt>
        <dd>{reserva.evento_nombre}</dd>
        <dt>Sector</dt>
        <dd>{reserva.sector_nombre}</dd>
        <dt>Entradas</dt>
        <dd>{reserva.cantidad}</dd>
        <dt>Total</dt>
        <dd>{pesos(reserva.monto_clp ?? 0)}</dd>
        {children}
      </dl>
    </div>
  );
}

export function CompraPage() {
  const { id = "" } = useParams();
  const { datos: reserva, error, cargando, recargar, setDatos } = useCarga(
    () => api.reserva(id),
    [id],
  );
  const [enviando, setEnviando] = useState(false);
  const [errorPago, setErrorPago] = useState<string | null>(null);

  const pendiente = reserva?.estado === "PENDIENTE_PAGO";
  const ahora = usarSegundero(pendiente);
  const restante = reserva ? new Date(reserva.vence_en).getTime() - ahora : 0;
  const plazoVencido = pendiente && restante <= 0;

  // El pago es asíncrono: el resultado llega por RabbitMQ, así que se consulta hasta tenerlo.
  useEffect(() => {
    if (reserva?.estado !== "PAGANDO") return;
    const intervalo = setInterval(() => void recargar(), INTERVALO_CONSULTA_MS);
    return () => clearInterval(intervalo);
  }, [reserva?.estado, recargar]);

  async function pagar(resultado: "aprobar" | "rechazar") {
    setEnviando(true);
    setErrorPago(null);
    try {
      setDatos(await api.pagar(id, resultado));
    } catch (e) {
      setErrorPago(e instanceof ErrorApi ? e.message : "No pudimos procesar el pago.");
      await recargar();
    } finally {
      setEnviando(false);
    }
  }

  if (cargando) return <p className="cargando">Cargando tu reserva…</p>;
  if (error || !reserva) {
    return (
      <p className="aviso aviso-error" role="alert">
        {error ?? "No encontramos esta reserva."}
      </p>
    );
  }

  if (reserva.estado === "CONFIRMADA") {
    return (
      <section className="centrada resultado">
        <h1>¡Listo, nos vemos allá!</h1>
        <p className="aviso aviso-exito" role="status">
          Pagaste {pesos(reserva.monto_clp ?? 0)}. Te enviamos las entradas por correo.
        </p>
        <Link to="/mis-entradas" className="boton boton-acento">
          Ver mis entradas
        </Link>
      </section>
    );
  }

  if (reserva.estado === "PAGANDO") {
    return (
      <section className="centrada resultado" role="status">
        <div className="giratorio" aria-hidden="true" />
        <h1>Procesando tu pago…</h1>
        <p>No cierres esta ventana, solo tardará unos segundos.</p>
      </section>
    );
  }

  if (reserva.estado !== "PENDIENTE_PAGO" || plazoVencido) {
    const rechazada = reserva.estado === "RECHAZADA";
    return (
      <section className="centrada resultado">
        <h1>{rechazada ? "El pago fue rechazado" : "Tu reserva venció"}</h1>
        <p className="aviso aviso-error" role="alert">
          {rechazada
            ? "No se hizo ningún cobro y liberamos tus cupos."
            : "Pasó el plazo de 10 minutos y liberamos tus cupos."}
        </p>
        {reserva.evento_id && (
          <Link to={`/eventos/${reserva.evento_id}`} className="boton">
            Volver a intentarlo
          </Link>
        )}
      </section>
    );
  }

  return (
    <section className="centrada">
      <h1>Paga tu reserva</h1>
      <Resumen reserva={reserva}>
        <dt>Tiempo restante</dt>
        <dd className="reloj" role="timer">
          {cuentaRegresiva(restante)}
        </dd>
      </Resumen>
      {errorPago && (
        <p className="aviso aviso-error" role="alert" style={{ marginTop: "1rem" }}>
          {errorPago}
        </p>
      )}
      <div className="acciones-pago">
        <button
          type="button"
          className="boton boton-acento"
          disabled={enviando}
          onClick={() => pagar("aprobar")}
        >
          Simular pago aprobado
        </button>
        <button
          type="button"
          className="boton boton-borde"
          disabled={enviando}
          onClick={() => pagar("rechazar")}
        >
          Simular pago rechazado
        </button>
      </div>
      <p className="nota">Es un pago simulado: no se piden datos de tarjeta ni se cobra nada.</p>
    </section>
  );
}
