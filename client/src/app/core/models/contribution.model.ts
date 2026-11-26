export interface PeerEvaluation {
  id: number;
  fase: number;
  evaluador_id: number;
  evaluado_id: number;
  comunicacion: number;
  calidad: number;
  compromiso: number;
  puntuacion: number;
  confirma_aporte: boolean;
  comentario: string | null;
  fortaleza: string | null;
  mejora: string | null;
}

export interface PeerEvaluationInput {
  evaluado_id: number;
  comunicacion: number;
  calidad: number;
  compromiso: number;
  confirma_aporte: boolean;
  fortaleza: string | null;
  mejora: string | null;
}

/** Lo que el equipo le dijo a la persona en una fase cerrada (sin nombres). */
export interface PhaseFeedback {
  fase: number;
  evaluaciones: number;
  comunicacion: number | null;
  calidad: number | null;
  compromiso: number | null;
  promedio: number | null;
  confirmaciones: number;
  fortalezas: string[];
  mejoras: string[];
  comentarios: string[];
  anonima: boolean;
}

export interface MyFeedback {
  fases: PhaseFeedback[];
  fase_en_curso: number | null;
}

export interface MemberContribution {
  usuario_id: number;
  nombre: string;
  rol: string;
  puntos_aprobados: number;
  puntos_validados: number;
  porcentaje: number;
  cumple: boolean;
  confirmaciones: number;
  evaluaciones_recibidas: number;
  evaluaciones_pendientes: number;
  promedio_evaluacion: number | null;
}

export interface ContributionSummary {
  fase: number;
  estado_proyecto: string;
  porcentaje_minimo: number;
  puntos_fase: number;
  parte_justa: number;
  integrantes: MemberContribution[];
  mis_evaluaciones: PeerEvaluation[];
  checkin_abierto: boolean;
  aviso: string | null;
  puede_cerrar: boolean;
  pendientes_cierre: string[];
}

export interface DeclarationMember {
  usuario_id: number;
  nombre: string;
  rol: string;
  puntos_validados: number;
  porcentaje: number;
  actividades: string[];
  firmado: boolean;
  firmado_en: string | null;
}

export interface Declaration {
  proyecto_id: number;
  nombre_proyecto: string;
  concluido_en: string | null;
  puntos_totales: number;
  integrantes: DeclarationMember[];
  puedo_firmar: boolean;
  motivo: string | null;
}
