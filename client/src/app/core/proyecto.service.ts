import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { API_URL } from './auth.service';
import { Invitation, Project, ProjectListResponse, ProjectMember } from './models/project.model';

@Injectable({ providedIn: 'root' })
export class ProyectoService {
  private readonly http = inject(HttpClient);
  readonly projects = signal<Project[]>([]);
  readonly invitations = signal<Invitation[]>([]);

  loadMine(): Observable<ProjectListResponse> {
    return this.http.get<ProjectListResponse>(`${API_URL}/proyectos`).pipe(
      tap((response) => {
        this.projects.set(response.proyectos);
        this.invitations.set(response.invitaciones_pendientes);
      }),
    );
  }

  create(payload: { nombre: string; descripcion: string | null }): Observable<Project> {
    return this.http.post<Project>(`${API_URL}/proyectos`, payload);
  }

  respondToInvitation(id: number, respuesta: 'aceptar' | 'rechazar'): Observable<Invitation> {
    return this.http.post<Invitation>(`${API_URL}/invitaciones/${id}/responder`, { respuesta });
  }

  getById(id: number): Observable<Project> {
    return this.http.get<Project>(`${API_URL}/proyectos/${id}`);
  }

  getMembers(projectId: number): Observable<ProjectMember[]> {
    return this.http.get<ProjectMember[]>(`${API_URL}/proyectos/${projectId}/integrantes`);
  }

  invite(projectId: number, correo: string): Observable<Invitation> {
    return this.http.post<Invitation>(`${API_URL}/proyectos/${projectId}/invitaciones`, { correo });
  }
}
