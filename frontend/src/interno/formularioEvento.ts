/** Estado del formulario de nuevo evento. Todo se guarda como texto, tal como lo escribe la persona. */
export interface FormularioSector {
  nombre: string;
  precio: string;
  capacidad: string;
}

export interface FormularioEvento {
  nombre: string;
  lugar: string;
  fecha: string;
  descripcion: string;
  sectores: FormularioSector[];
}

/** Cuerpo que espera la API para crear un evento. */
export interface DatosEvento {
  nombre: string;
  lugar: string;
  fecha: string;
  descripcion: string;
  sectores: { nombre: string; precio_clp: number; capacidad: number }[];
}

/**
 * Convierte el texto del formulario en el cuerpo de la API.
 * Es pura para poder probarla sin React: la fecha local de datetime-local pasa a ISO en UTC.
 */
export function aDatosDeEvento(formulario: FormularioEvento): DatosEvento {
  return {
    nombre: formulario.nombre.trim(),
    lugar: formulario.lugar.trim(),
    fecha: new Date(formulario.fecha).toISOString(),
    descripcion: formulario.descripcion.trim(),
    sectores: formulario.sectores.map((sector) => ({
      nombre: sector.nombre.trim(),
      precio_clp: Number(sector.precio),
      capacidad: Number(sector.capacidad),
    })),
  };
}
