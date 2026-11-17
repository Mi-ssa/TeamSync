import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, of, switchMap, tap } from 'rxjs';
import { LoginRequest, RegisterRequest, TokenResponse, User } from './models/user.model';

export const API_URL = 'http://127.0.0.1:8000';
const TOKEN_KEY = 'teamsync_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  readonly user = signal<User | null>(null);

  get token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  register(payload: RegisterRequest): Observable<User> {
    return this.http.post<User>(`${API_URL}/auth/register`, payload);
  }

  login(payload: LoginRequest): Observable<User> {
    return this.http.post<TokenResponse>(`${API_URL}/auth/login`, payload).pipe(
      tap((response) => localStorage.setItem(TOKEN_KEY, response.access_token)),
      switchMap(() => this.http.get<User>(`${API_URL}/auth/me`)),
      tap((user) => this.user.set(user)),
    );
  }

  restoreSession(): Observable<User | null> {
    if (this.user()) {
      return of(this.user());
    }
    if (!this.token) {
      return of(null);
    }
    return this.http.get<User>(`${API_URL}/auth/me`).pipe(
      tap((user) => this.user.set(user)),
      catchError(() => {
        this.clearSession();
        return of(null);
      }),
    );
  }

  ensureCurrentUser(): Observable<boolean> {
    if (this.user()) {
      return of(true);
    }
    if (!this.token) {
      return of(false);
    }
    return this.restoreSession().pipe(switchMap((user) => of(user !== null)));
  }

  clearSession(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.user.set(null);
  }

  logout(): void {
    this.clearSession();
    void this.router.navigateByUrl('/login');
  }
}
