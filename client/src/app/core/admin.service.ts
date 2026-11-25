import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_URL } from './auth.service';
import { AdminReport, AdminSettings } from './models/admin.model';
import { User } from './models/user.model';

@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly http = inject(HttpClient);

  users(): Observable<User[]> {
    return this.http.get<User[]>(`${API_URL}/admin/usuarios`);
  }

  updateUser(id: number, changes: { activo?: boolean; es_admin?: boolean }): Observable<User> {
    return this.http.patch<User>(`${API_URL}/admin/usuarios/${id}`, changes);
  }

  settings(): Observable<AdminSettings> {
    return this.http.get<AdminSettings>(`${API_URL}/admin/configuracion`);
  }

  saveSettings(settings: AdminSettings): Observable<AdminSettings> {
    return this.http.put<AdminSettings>(`${API_URL}/admin/configuracion`, settings);
  }

  report(): Observable<AdminReport> {
    return this.http.get<AdminReport>(`${API_URL}/admin/reportes`);
  }
}
