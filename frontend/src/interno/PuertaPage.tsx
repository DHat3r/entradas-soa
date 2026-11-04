import { useRef, useState, type FormEvent } from "react";
import { api, ErrorApi, type ResultadoValidacion } from "../lib/api";
import { fechaLarga } from "../lib/formato";

/** Lo que muestra el panel después de validar: el color nunca va solo, hay texto y símbolo. */
interface Panel {
  tono: "ok" | "error";
  simbolo: "✓" | "✕";
  titulo: string;
  detalles: string[];
}

function panelDeResultado(resultado: ResultadoValidacion): Panel {
  const entrada = resultado.entrada;

  if (resultado.resultado === "valida") {
    return {
      tono: "ok",
      simbolo: "✓",
      titulo: "Puede entrar",
      detalles: entrada
        ? [
            `Evento: ${entrada.evento_nombre}`,
            `Sector: ${entrada.sector_nombre}`,
            `Entrada número ${entrada.numero}`,
          ]
        : [],
    };
  }

  if (resultado.resultado === "ya_usada") {
    return {
      tono: "error",
      simbolo: "✕",
      titulo: "Entrada ya usada",
      detalles: entrada?.usada_en ? [`Usada el ${fechaLarga(entrada.usada_en)}`] : [],
    };
  }

  return { tono: "error", simbolo: "✕", titulo: "Código inválido", detalles: [] };
}

function panelDeError(e: unknown): Panel {
  if (e instanceof ErrorApi && e.estado === 404) {
    return { tono: "error", simbolo: "✕", titulo: "Entrada no encontrada", detalles: [] };
  }
  const mensaje = e instanceof ErrorApi ? e.message : "Algo salió mal. Intenta de nuevo.";
  return { tono: "error", simbolo: "✕", titulo: mensaje, detalles: [] };
}

export function PuertaPage() {
  const [codigo, setCodigo] = useState("");
  const [panel, setPanel] = useState<Panel | null>(null);
  const campo = useRef<HTMLInputElement>(null);

  async function validar(formulario: FormEvent) {
    formulario.preventDefault();
    const valor = codigo.trim();
    if (!valor) return;

    // Se limpia antes de esperar la respuesta, para que el lector pueda seguir con la siguiente entrada.
    setCodigo("");
    try {
      setPanel(panelDeResultado(await api.validarEntrada(valor)));
    } catch (e) {
      setPanel(panelDeError(e));
    } finally {
      campo.current?.focus();
    }
  }

  return (
    <section className="in-puerta">
      <h1>Control de entradas</h1>

      <form className="formulario" onSubmit={validar}>
        <label className="campo in-campo-grande">
          Código de la entrada
          <input
            ref={campo}
            autoFocus
            autoComplete="off"
            spellCheck={false}
            required
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            aria-describedby="ayuda-codigo"
          />
          <small id="ayuda-codigo">Escanea el QR con un lector o pega el código</small>
        </label>
      </form>

      <section
        className={`in-panel ${panel ? `in-panel-${panel.tono}` : "in-panel-espera"}`}
        role="status"
        aria-live="polite"
      >
        {panel ? (
          <>
            <span className="in-simbolo" aria-hidden="true">
              {panel.simbolo}
            </span>
            <div>
              <h2>{panel.titulo}</h2>
              {panel.detalles.map((linea) => (
                <p key={linea}>{linea}</p>
              ))}
            </div>
          </>
        ) : (
          <p>Esperando el próximo código.</p>
        )}
      </section>
    </section>
  );
}
