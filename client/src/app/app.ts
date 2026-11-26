import { Component, effect, inject } from '@angular/core';
import { Router, RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';
import { NotificationBellComponent } from './core/notification-bell.component';
import { NotificacionService } from './core/notificacion.service';

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterOutlet, NotificationBellComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly auth = inject(AuthService);
  readonly router = inject(Router);
  private readonly notifications = inject(NotificacionService);

  constructor() {
    // Las notificaciones se consultan solo mientras hay una sesión iniciada.
    effect(() => {
      if (this.auth.user()) {
        this.notifications.start();
      } else {
        this.notifications.stop();
      }
    });
  }
}
