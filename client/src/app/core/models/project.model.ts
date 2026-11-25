export interface Project {
  id: number;
  nombre: string;
  descripcion: string | null;
  creado_por_id: number;
  fase_actual: number;
  estado: 'activo' | 'concluido';
  creado_en: string;
}

export interface Invitation {
  id: number;
  proyecto_id: number;
  usuario_id: number;
  rol: string;
  estado: string;
  creado_en: string;
  nombre_proyecto: string;
}

export interface ProjectListResponse {
  proyectos: Project[];
  invitaciones_pendientes: Invitation[];
}

export interface ProjectMember {
  id: number;
  nombre: string;
  correo: string;
  rol: string;
}
