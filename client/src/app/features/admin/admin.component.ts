import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize, forkJoin } from 'rxjs';
import { AdminService } from '../../core/admin.service';
import { apiErrorMessage } from '../../core/api-error';
import { AuthService } from '../../core/auth.service';
import { AdminReport } from '../../core/models/admin.model';
import { User } from '../../core/models/user.model';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './admin.component.html',
})
export class AdminComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly admin = inject(AdminService);
  readonly auth = inject(AuthService);
  readonly users = signal<User[]>([]);
  readonly report = signal<AdminReport | null>(null);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly updatingUser = signal<number | null>(null);
  readonly error = signal('');
  readonly message = signal('');
  readonly settingsForm = this.fb.nonNullable.group({
    porcentaje_minimo: [70, [Validators.required, Validators.min(0), Validators.max(100)]],
    dias_inactividad: [5, [Validators.required, Validators.min(1), Validators.max(365)]],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    forkJoin({
      users: this.admin.users(),
      settings: this.admin.settings(),
      report: this.admin.report(),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: ({ users, settings, report }) => {
          this.users.set(users);
          this.report.set(report);
          this.settingsForm.setValue(settings);
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo cargar el panel de administración.')),
      });
  }

  saveSettings(): void {
    if (this.settingsForm.invalid || this.saving()) {
      this.settingsForm.markAllAsTouched();
      return;
    }
    const value = this.settingsForm.getRawValue();
    this.saving.set(true);
    this.message.set('');
    this.admin
      .saveSettings({
        porcentaje_minimo: Number(value.porcentaje_minimo),
        dias_inactividad: Number(value.dias_inactividad),
      })
      .pipe(finalize(() => this.saving.set(false)))
      .subscribe({
        next: () => {
          this.message.set('Parámetros guardados.');
          this.admin.report().subscribe((report) => this.report.set(report));
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudieron guardar los parámetros.')),
      });
  }

  toggle(user: User, field: 'activo' | 'es_admin'): void {
    this.updatingUser.set(user.id);
    this.error.set('');
    this.admin
      .updateUser(user.id, { [field]: !user[field] })
      .pipe(finalize(() => this.updatingUser.set(null)))
      .subscribe({
        next: (updated) => {
          this.users.update((users) => users.map((u) => (u.id === updated.id ? updated : u)));
          this.admin.report().subscribe((report) => this.report.set(report));
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo actualizar el usuario.')),
      });
  }
}
