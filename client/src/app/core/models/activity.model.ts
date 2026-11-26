export interface Activity {
  id: number;
  proyecto_id: number;
  responsable_id: number;
  nombre: string;
  descripcion: string | null;
  puntos_acordados: number;
  estado: 'votacion' | 'pendiente' | 'completada';
  fase: number;
  votos_emitidos: number;
  votos_requeridos: number;
  mi_voto: number | null;
  creado_en: string;
}

/** Agradecimiento de un compañero por un avance aprobado (no suma puntos). */
export interface ProgressThanks {
  id: number;
  de_usuario_id: number;
  de_nombre: string;
  mensaje: string;
  creado_en: string;
}

export interface Progress {
  id: number;
  actividad_id: number;
  usuario_id: number;
  descripcion: string;
  url_evidencia: string | null;
  estado: 'pendiente' | 'aprobado' | 'rechazado';
  comentario_revision: string | null;
  creado_en: string;
  revisado_en: string | null;
  agradecimientos: ProgressThanks[];
}
