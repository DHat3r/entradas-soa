import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useCarga } from "../lib/useCarga";

export function MisEntradasPage() {
  const { datos: entradas, error, cargando } = useCarga(api.misEntradas);

  return (
    <section style={{ paddingTop: "1.5rem" }}>
      <h1 style={{ fontSize: "clamp(2rem, 6vw, 3rem)", fontWeight: 800, marginBottom: "1.25rem" }}>
        Mis entradas
      </h1>
      {cargando && <p className="cargando">Cargando tus entradas…</p>}
      {error && (
        <p className="aviso aviso-error" role="alert">
          {error}
        </p>
      )}
      {entradas?.length === 0 && (
        <div className="vacio">
          <p>Todavía no tienes entradas.</p>
          <Link to="/" className="boton" style={{ marginTop: "1rem" }}>
            Ver eventos
          </Link>
        </div>
      )}
      {entradas && entradas.length > 0 && (
        <ul className="tarjetas">
          {entradas.map((entrada) => (
            <li key={entrada.id}>
              <article className={`entrada-qr ${entrada.usada_en ? "usada" : ""}`}>
                <h3>{entrada.evento_nombre}</h3>
                <p>
                  {entrada.sector_nombre} · Entrada {entrada.numero}
                </p>
                <img src={entrada.qr} alt={`Código QR de la entrada ${entrada.numero}`} />
                <span
                  className={`etiqueta ${entrada.usada_en ? "etiqueta-usada" : "etiqueta-disponible"}`}
                >
                  {entrada.usada_en ? "Ya usada" : "Lista para usar"}
                </span>
                {!entrada.usada_en && (
                  <button
                    type="button"
                    className="enlace"
                    onClick={() => void navigator.clipboard.writeText(entrada.codigo)}
                  >
                    Copiar código
                  </button>
                )}
              </article>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
