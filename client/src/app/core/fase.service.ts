import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from './auth.service';
import {
  ContributionSummary,
  Declaration,
  MyFeedback,
  PeerEvaluation,
  PeerEvaluationInput,
} from './models/contribution.model';
import { Project } from './models/project.model';

@Injectable({ providedIn: 'root' })
export class FaseService {
  private readonly http = inject(HttpClient);

  contribution(projectId: number): Observable<ContributionSummary> {
    return this.http.get<ContributionSummary>(`${API_URL}/proyectos/${projectId}/contribucion`);
  }

  evaluate(projectId: number, payload: PeerEvaluationInput): Observable<PeerEvaluation> {
    return this.http.post<PeerEvaluation>(`${API_URL}/proyectos/${projectId}/evaluaciones`, payload);
  }

  myFeedback(projectId: number): Observable<MyFeedback> {
    return this.http.get<MyFeedback>(`${API_URL}/proyectos/${projectId}/mi-retroalimentacion`);
  }

  closePhase(projectId: number): Observable<Project> {
    return this.http.post<Project>(`${API_URL}/proyectos/${projectId}/cerrar-fase`, {});
  }

  conclude(projectId: number): Observable<Project> {
    return this.http.post<Project>(`${API_URL}/proyectos/${projectId}/concluir`, {});
  }

  declaration(projectId: number): Observable<Declaration> {
    return this.http.get<Declaration>(`${API_URL}/proyectos/${projectId}/declaracion`);
  }

  sign(projectId: number): Observable<Declaration> {
    return this.http.post<Declaration>(`${API_URL}/proyectos/${projectId}/declaracion/firmar`, {});
  }
}
