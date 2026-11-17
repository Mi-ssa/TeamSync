import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { API_URL } from './auth.service';
import { Activity, Progress } from './models/activity.model';

@Injectable({ providedIn: 'root' })
export class ActividadService {
  private readonly http = inject(HttpClient);
  readonly activities = signal<Activity[]>([]);
  readonly advances = signal<Record<number, Progress[]>>({});

  loadForProject(projectId: number): Observable<Activity[]> {
    return this.http
      .get<Activity[]>(`${API_URL}/proyectos/${projectId}/actividades`)
      .pipe(
        tap((activities) => {
          this.activities.set(activities);
          this.advances.set({});
        }),
      );
  }

  create(projectId: number, payload: {
    nombre: string;
    descripcion: string | null;
    puntos_acordados: number;
    responsable_id: number;
  }): Observable<Activity> {
    return this.http.post<Activity>(`${API_URL}/proyectos/${projectId}/actividades`, payload).pipe(
      tap((activity) => this.activities.update((current) => [...current, activity])),
    );
  }

  loadAdvances(activityId: number): Observable<Progress[]> {
    return this.http
      .get<Progress[]>(`${API_URL}/actividades/${activityId}/avances`)
      .pipe(tap((advances) => this.setAdvances(activityId, advances)));
  }

  submitAdvance(
    activityId: number,
    payload: { descripcion: string; url_evidencia: string | null },
  ): Observable<Progress> {
    return this.http
      .post<Progress>(`${API_URL}/actividades/${activityId}/avances`, payload)
      .pipe(
        tap((advance) =>
          this.setAdvances(activityId, [...(this.advances()[activityId] ?? []), advance]),
        ),
      );
  }

  reviewAdvance(id: number, activityId: number, estado: 'aprobado' | 'rechazado'): Observable<Progress> {
    return this.http
      .patch<Progress>(`${API_URL}/avances/${id}/revisar`, { estado })
      .pipe(
        tap((updated) => {
          const current = this.advances()[activityId] ?? [];
          this.setAdvances(
            activityId,
            current.map((advance) => (advance.id === id ? updated : advance)),
          );
          if (estado === 'aprobado') {
            this.activities.update((activities) =>
              activities.map((activity) =>
                activity.id === activityId ? { ...activity, estado: 'completada' } : activity,
              ),
            );
          }
        }),
      );
  }

  activityStatus(activity: Activity): 'pendiente' | 'en_revision' | 'aprobada' {
    if (activity.estado === 'completada') {
      return 'aprobada';
    }
    return (this.advances()[activity.id] ?? []).some((advance) => advance.estado === 'pendiente')
      ? 'en_revision'
      : 'pendiente';
  }

  private setAdvances(activityId: number, advances: Progress[]): void {
    this.advances.update((current) => ({ ...current, [activityId]: advances }));
  }
}
