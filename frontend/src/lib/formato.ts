const ZONA = "America/Santiago";

export function pesos(monto: number): string {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(monto);
}

export function fechaLarga(iso: string): string {
  return new Intl.DateTimeFormat("es-CL", {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: ZONA,
  }).format(new Date(iso));
}

export function diaYMes(iso: string): { dia: string; mes: string } {
  const fecha = new Date(iso);
  return {
    dia: new Intl.DateTimeFormat("es-CL", { day: "2-digit", timeZone: ZONA }).format(fecha),
    mes: new Intl.DateTimeFormat("es-CL", { month: "short", timeZone: ZONA })
      .format(fecha)
      .replace(".", ""),
  };
}

export function cuentaRegresiva(milisegundos: number): string {
  const total = Math.max(0, Math.ceil(milisegundos / 1000));
  const minutos = Math.floor(total / 60);
  const segundos = String(total % 60).padStart(2, "0");
  return `${minutos}:${segundos}`;
}

export function precioDesde(precios: number[]): number {
  return Math.min(...precios);
}
