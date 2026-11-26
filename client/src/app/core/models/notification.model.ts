export type NotificationKind =
  | 'invitacion'
  | 'equipo'
  | 'votacion'
  | 'actividad'
  | 'revision'
  | 'resultado'
  | 'checkin'
  | 'fase'
  | 'declaracion'
  | 'recordatorio'
  | 'retroalimentacion'
  | 'agradecimiento';

export interface AppNotification {
  id: number;
  tipo: NotificationKind;
  titulo: string;
  mensaje: string;
  enlace: string;
  leida: boolean;
  creado_en: string;
}

export interface NotificationList {
  no_leidas: number;
  notificaciones: AppNotification[];
}
