import { Component, ElementRef, HostListener, inject, signal } from '@angular/core';
import { NotificacionService } from './notificacion.service';
import { AppNotification, NotificationKind } from './models/notification.model';

const ICONS: Record<NotificationKind, string> = {
  invitacion: '✉',
  equipo: '♧',
  votacion: '✦',
  actividad: '☷',
  revision: '✓',
  resultado: '↗',
  checkin: '★',
  fase: '▥',
  declaracion: '✍',
  recordatorio: '⏰',
  retroalimentacion: '✎',
  agradecimiento: '♥',
};

@Component({
  selector: 'app-notification-bell',
  standalone: true,
  template: `
    <div class="notif">
      <button
        class="notif-trigger"
        type="button"
        [attr.aria-expanded]="open()"
        aria-haspopup="true"
        aria-controls="notif-panel"
        [attr.aria-label]="notifications.unread() ? 'Notificaciones, ' + notifications.unread() + ' sin leer' : 'Notificaciones'"
        (click)="toggle()"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path d="M6 9a6 6 0 1 1 12 0c0 6 2.5 7.5 2.5 7.5h-17S6 15 6 9Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
          <path d="M10 20a2.2 2.2 0 0 0 4 0" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
        @if (notifications.unread()) {
          <span class="notif-badge" aria-hidden="true">{{ notifications.unread() > 9 ? '9+' : notifications.unread() }}</span>
        }
      </button>

      @if (open()) {
        <section class="notif-panel" id="notif-panel" aria-label="Notificaciones">
          <header class="notif-header">
            <h2>Notificaciones</h2>
            @if (notifications.unread()) {
              <button class="notif-link" type="button" (click)="notifications.markAllRead()">Marcar todas como leídas</button>
            }
          </header>

          @switch (notifications.permission()) {
            @case ('default') {
              <div class="notif-permission">
                <p>Activa los avisos del navegador para enterarte aunque estés en otra pestaña.</p>
                <button class="button button-small" type="button" (click)="notifications.enableBrowserNotifications()">Activar avisos</button>
              </div>
            }
            @case ('denied') {
              <p class="notif-permission notif-permission-muted">
                Los avisos del navegador están bloqueados. Puedes permitirlos desde el candado junto a la dirección del sitio.
              </p>
            }
          }

          @if (notifications.items().length) {
            <ul class="notif-list">
              @for (item of notifications.items(); track item.id) {
                <li>
                  <button class="notif-item" [class.notif-unread]="!item.leida" type="button" (click)="select(item)">
                    <span class="notif-icon" aria-hidden="true">{{ icon(item) }}</span>
                    <span class="notif-body">
                      <strong>{{ item.titulo }}</strong>
                      <span>{{ item.mensaje }}</span>
                      <time [attr.datetime]="item.creado_en">{{ ago(item.creado_en) }}</time>
                    </span>
                    @if (!item.leida) {
                      <span class="notif-dot"><span class="sr-only">Sin leer</span></span>
                    }
                  </button>
                </li>
              }
            </ul>
          } @else {
            <p class="notif-empty">No tienes notificaciones.</p>
          }
        </section>
      }
    </div>

    @if (notifications.toast(); as toast) {
      <div class="notif-toast" role="status" aria-live="polite">
        <button class="notif-toast-body" type="button" (click)="notifications.open(toast)">
          <span class="notif-icon" aria-hidden="true">{{ icon(toast) }}</span>
          <span class="notif-body">
            <strong>{{ toast.titulo }}</strong>
            <span>{{ toast.mensaje }}</span>
          </span>
        </button>
        <button class="notif-toast-close" type="button" aria-label="Cerrar aviso" (click)="notifications.dismissToast()">×</button>
      </div>
    }
  `,
})
export class NotificationBellComponent {
  readonly notifications = inject(NotificacionService);
  private readonly host = inject(ElementRef<HTMLElement>);
  readonly open = signal(false);

  toggle(): void {
    this.open.update((value) => !value);
    if (this.open()) {
      this.notifications.refresh();
    }
  }

  select(item: AppNotification): void {
    this.open.set(false);
    this.notifications.open(item);
  }

  icon(item: AppNotification): string {
    return ICONS[item.tipo] ?? '•';
  }

  ago(iso: string): string {
    const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 60) return 'hace un momento';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `hace ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `hace ${hours} h`;
    const days = Math.floor(hours / 24);
    return days === 1 ? 'ayer' : `hace ${days} días`;
  }

  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(event.target as Node)) {
      this.open.set(false);
    }
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.open.set(false);
  }
}
