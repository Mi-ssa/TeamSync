export interface AdminSettings {
  porcentaje_minimo: number;
  dias_inactividad: number;
}

export interface ProjectReport {
  id: number;
  nombre: string;
  lider: string;
  estado: string;
  fase_actual: number;
  integrantes: number;
  actividades: number;
  actividades_completadas: number;
  puntos_totales: number;
  puntos_validados: number;
  integrantes_bajo_minimo: number;
  integrantes_inactivos: number;
}

export interface AdminReport {
  usuarios: number;
  usuarios_activos: number;
  proyectos: number;
  proyectos_concluidos: number;
  porcentaje_minimo: number;
  dias_inactividad: number;
  detalle: ProjectReport[];
}
