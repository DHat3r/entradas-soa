/** Cliente de la API. La sesión viaja en una cookie httpOnly que JavaScript no puede leer. */

export type Rol = "cliente" | "organizador" | "validador";

export interface Usuario {
  usuario_id: string;
  rol: Rol;
  correo: string;
  nombre: string;
}

export interface Sector {
  id: string;
  nombre: string;
  precio_clp: number;
  capacidad: number;
  disponibles: number;
  vendidos: number;
}

export interface Evento {
  id: string;
  nombre: string;
  descripcion: string;
  lugar: string;
  fecha: string;
  estado: "BORRADOR" | "PUBLICADO";
  sectores: Sector[];
}

export type EstadoReserva =
  | "CREADA"
  | "CANCELADA"
  | "PENDIENTE_PAGO"
  | "VENCIDA"
  | "PAGANDO"
  | "CONFIRMADA"
  | "RECHAZADA";

export interface Reserva {
  id: string;
  estado: EstadoReserva;
  cantidad: number;
  monto_clp: number | null;
  evento_id: string | null;
  evento_nombre: string | null;
  sector_nombre: string | null;
  vence_en: string;
}

export interface Entrada {
  id: string;
  evento_nombre: string;
  sector_nombre: string;
  numero: number;
  usada_en: string | null;
  codigo: string;
  qr: string;
}

export interface ResultadoValidacion {
  resultado: "valida" | "ya_usada" | "invalida";
  mensaje: string;
  entrada?: Omit<Entrada, "qr" | "codigo">;
}

export class ErrorApi extends Error {
  constructor(
    readonly estado: number,
    readonly codigo: string,
    mensaje: string,
  ) {
    super(mensaje);
  }
}

export async function pedir<T>(ruta: string, opciones: { metodo?: string; datos?: unknown } = {}) {
  let respuesta: Response;
  try {
    respuesta = await fetch(`/api${ruta}`, {
      method: opciones.metodo ?? (opciones.datos === undefined ? "GET" : "POST"),
      headers: opciones.datos === undefined ? undefined : { "Content-Type": "application/json" },
      body: opciones.datos === undefined ? undefined : JSON.stringify(opciones.datos),
    });
  } catch {
    throw new ErrorApi(0, "sin_conexion", "No pudimos conectarnos. Revisa tu conexión.");
  }

  if (respuesta.status === 204) return undefined as T;
  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    throw new ErrorApi(
      respuesta.status,
      cuerpo?.codigo ?? "error",
      cuerpo?.mensaje ?? "Algo salió mal. Intenta de nuevo.",
    );
  }
  return cuerpo as T;
}

export const api = {
  yo: () => pedir<Usuario>("/auth/yo"),
  ingresar: (correo: string, password: string) =>
    pedir<unknown>("/auth/login", { datos: { correo, password } }),
  registrar: (nombre: string, correo: string, password: string) =>
    pedir<unknown>("/auth/registro", { datos: { nombre, correo, password } }),
  salir: () => pedir<void>("/auth/logout", { metodo: "POST" }),

  eventos: () => pedir<Evento[]>("/eventos"),
  evento: (id: string) => pedir<Evento>(`/eventos/${id}`),
  misEventos: () => pedir<Evento[]>("/interno/eventos"),
  crearEvento: (datos: unknown) => pedir<Evento>("/eventos", { datos }),
  publicarEvento: (id: string) => pedir<Evento>(`/eventos/${id}/publicar`, { metodo: "POST" }),

  reservar: (sector_id: string, cantidad: number) =>
    pedir<Reserva>("/reservas", { datos: { sector_id, cantidad } }),
  reserva: (id: string) => pedir<Reserva>(`/reservas/${id}`),
  pagar: (id: string, resultado_simulado: "aprobar" | "rechazar") =>
    pedir<Reserva>(`/reservas/${id}/pagar`, { datos: { resultado_simulado } }),

  misEntradas: () => pedir<Entrada[]>("/entradas"),
  validarEntrada: (codigo: string) =>
    pedir<ResultadoValidacion>("/entradas/validar", { datos: { codigo } }),
};
