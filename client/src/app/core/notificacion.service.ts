import { HttpClient } from '@angular/common/http';
import { Injectable, NgZone, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { API_URL } from './auth.service';
import { AppNotification, NotificationList } from './models/notification.model';

type BrowserPermission = NotificationPermission | 'unsupported';

/**
 * Notificaciones de TeamSync.
 * - Consulta el servidor cada 15 s mientras hay sesión (y al volver a la pestaña).
 * - Si llega algo nuevo y la pestaña no está a la vista, muestra la notificación
 *   del sistema (API Notification del navegador); si está a la vista, un aviso
 *   dentro de la app.
 * - Sin service worker: los avisos del sistema llegan mientras TeamSync esté
 *   abierto en alguna pestaña, aunque sea en segundo plano.
 */
@Injectable({ providedIn: 'root' })
export class NotificacionService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly zone = inject(NgZone);

  readonly items = signal<AppNotification[]>([]);
  readonly unread = signal(0);
  readonly toast = signal<AppNotification | null>(null);
  readonly permission = signal<BrowserPermission>(
    typeof Notification === 'undefined' ? 'unsupported' : Notification.permission,
  );

  private polling?: Subscription;
  private lastSeenId: number | null = null;
  private toastTimer?: ReturnType<typeof setTimeout>;
  private readonly onVisible = () => {
    if (!document.hidden) {
      this.refresh();
    }
  };

  start(): void {
    if (this.polling) {
      return;
    }
    this.lastSeenId = null;
    this.refresh();
    this.polling = interval(15000).subscribe(() => this.refresh());
    document.addEventListener('visibilitychange', this.onVisible);
  }

  stop(): void {
    this.polling?.unsubscribe();
    this.polling = undefined;
    document.removeEventListener('visibilitychange', this.onVisible);
    this.items.set([]);
    this.unread.set(0);
    this.toast.set(null);
    this.lastSeenId = null;
  }

  refresh(): void {
    this.http.get<NotificationList>(`${API_URL}/notificaciones`).subscribe({
      next: (data) => this.apply(data),
      error: () => undefined, // un fallo de red no debe molestar; se reintenta solo
    });
  }

  markRead(item: AppNotification): void {
    if (item.leida) {
      return;
    }
    this.items.update((items) => items.map((n) => (n.id === item.id ? { ...n, leida: true } : n)));
    this.unread.update((n) => Math.max(0, n - 1));
    this.http.post(`${API_URL}/notificaciones/${item.id}/leer`, {}).subscribe({ error: () => undefined });
  }

  markAllRead(): void {
    this.http
      .post<NotificationList>(`${API_URL}/notificaciones/leer-todas`, {})
      .subscribe({ next: (data) => this.apply(data), error: () => undefined });
  }

  open(item: AppNotification): void {
    this.markRead(item);
    this.dismissToast();
    this.router.navigateByUrl(item.enlace);
  }

  async enableBrowserNotifications(): Promise<void> {
    if (typeof Notification === 'undefined') {
      return;
    }
    const result = await Notification.requestPermission();
    this.zone.run(() => this.permission.set(result));
  }

  dismissToast(): void {
    clearTimeout(this.toastTimer);
    this.toast.set(null);
  }

  private apply(data: NotificationList): void {
    this.items.set(data.notificaciones);
    this.unread.set(data.no_leidas);
    const maxId = data.notificaciones.reduce((max, n) => Math.max(max, n.id), 0);
    // La primera carga solo marca la línea base: no avisa de lo que ya existía.
    if (this.lastSeenId !== null) {
      const fresh = data.notificaciones
        .filter((n) => n.id > this.lastSeenId! && !n.leida)
        .sort((a, b) => a.id - b.id);
      if (fresh.length) {
        this.announce(fresh);
      }
    }
    this.lastSeenId = Math.max(this.lastSeenId ?? 0, maxId);
  }

  private announce(fresh: AppNotification[]): void {
    if (typeof Notification !== 'undefined') {
      this.permission.set(Notification.permission);
    }
    if (document.hidden && this.permission() === 'granted') {
      for (const item of fresh.slice(-3)) {
        const system = new Notification(item.titulo, {
          body: item.mensaje,
          icon: '/teamsync-mark.svg',
          tag: `teamsync-${item.id}`,
        });
        system.onclick = () =>
          this.zone.run(() => {
            window.focus();
            this.open(item);
            system.close();
          });
      }
      return;
    }
    // Con la pestaña a la vista basta un aviso discreto dentro de la app.
    const latest = fresh[fresh.length - 1];
    clearTimeout(this.toastTimer);
    this.toast.set(latest);
    this.toastTimer = setTimeout(() => this.zone.run(() => this.toast.set(null)), 6000);
  }
}
