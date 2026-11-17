export interface Activity {
  id: number;
  proyecto_id: number;
  responsable_id: number;
  nombre: string;
  descripcion: string | null;
  puntos_acordados: number;
  estado: string;
  creado_en: string;
}

export interface Progress {
  id: number;
  actividad_id: number;
  usuario_id: number;
  descripcion: string;
  url_evidencia: string | null;
  estado: 'pendiente' | 'aprobado' | 'rechazado';
  creado_en: string;
  revisado_en: string | null;
}
