import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { apiErrorMessage } from '../../core/api-error';
import { AuthService } from '../../core/auth.service';
import { ProyectoService } from '../../core/proyecto.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  readonly auth = inject(AuthService);
  readonly proyectoService = inject(ProyectoService);
  readonly showProjectModal = signal(false);
  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly respondingId = signal<number | null>(null);
  readonly error = signal('');
  readonly form = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(160)]],
    descripcion: [''],
  });

  ngOnInit(): void {
    this.loadProjects();
  }

  loadProjects(): void {
    this.loading.set(true);
    this.proyectoService
      .loadMine()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudieron cargar tus proyectos.')),
      });
  }

  createProject(): void {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }
    this.error.set('');
    this.submitting.set(true);
    const formValue = this.form.getRawValue();
    this.proyectoService
      .create({ nombre: formValue.nombre.trim(), descripcion: formValue.descripcion.trim() || null })
      .pipe(finalize(() => this.submitting.set(false)))
      .subscribe({
        next: () => {
          this.showProjectModal.set(false);
          this.form.reset();
          this.loadProjects();
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo crear el proyecto.')),
      });
  }

  answerInvitation(id: number, respuesta: 'aceptar' | 'rechazar'): void {
    this.respondingId.set(id);
    this.error.set('');
    this.proyectoService
      .respondToInvitation(id, respuesta)
      .pipe(finalize(() => this.respondingId.set(null)))
      .subscribe({
        next: () => this.loadProjects(),
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo responder la invitación.')),
      });
  }

  closeProjectModal(): void {
    this.showProjectModal.set(false);
    this.form.reset();
  }
}
