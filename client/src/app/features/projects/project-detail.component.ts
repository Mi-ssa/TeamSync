import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';
import { apiErrorMessage } from '../../core/api-error';
import { ActividadService } from '../../core/actividad.service';
import { AuthService } from '../../core/auth.service';
import { Activity, Progress } from '../../core/models/activity.model';
import { Project, ProjectMember } from '../../core/models/project.model';
import { ProyectoService } from '../../core/proyecto.service';

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [DatePipe, ReactiveFormsModule, RouterLink],
  templateUrl: './project-detail.component.html',
  styleUrl: './project-detail.component.css',
})
export class ProjectDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  private readonly projects = inject(ProyectoService);
  readonly auth = inject(AuthService);
  readonly activityService = inject(ActividadService);
  readonly project = signal<Project | null>(null);
  readonly members = signal<ProjectMember[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly inviteMessage = signal('');
  readonly inviting = signal(false);
  readonly showActivityForm = signal(false);
  readonly creatingActivity = signal(false);
  readonly activeAdvanceActivity = signal<number | null>(null);
  readonly sendingAdvance = signal(false);
  readonly reviewingAdvance = signal<number | null>(null);
  readonly rejectingAdvance = signal<number | null>(null);
  readonly rejectComment = signal('');
  readonly rejectError = signal('');
  readonly isLeader = computed(
    () => this.project()?.creado_por_id === this.auth.user()?.id,
  );
  readonly totalPoints = computed(() =>
    this.activityService.activities().reduce(
      (total, activity) => total + activity.puntos_acordados,
      0,
    ),
  );
  readonly approvedPoints = computed(() =>
    this.activityService
      .activities()
      .filter((activity) => activity.estado === 'completada')
      .reduce((total, activity) => total + activity.puntos_acordados, 0),
  );
  readonly overallProgress = computed(() =>
    this.totalPoints() > 0
      ? Math.round((this.approvedPoints() / this.totalPoints()) * 100)
      : 0,
  );
  private projectId = 0;

  readonly inviteForm = this.fb.nonNullable.group({
    correo: ['', [Validators.required, Validators.email]],
  });
  readonly activityForm = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(160)]],
    descripcion: [''],
    puntos_acordados: [1, [Validators.required, Validators.min(0)]],
    responsable_id: ['', Validators.required],
  });
  readonly advanceForm = this.fb.nonNullable.group({
    descripcion: ['', [Validators.required, Validators.maxLength(4000)]],
    url_evidencia: ['', Validators.pattern(/^$|^https?:\/\/.+/i)],
  });

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const id = Number(params.get('id'));
      if (Number.isInteger(id) && id > 0) {
        this.loadProject(id);
      }
    });
  }

  loadProject(id: number): void {
    this.projectId = id;
    this.loading.set(true);
    this.error.set('');
    forkJoin({
      project: this.projects.getById(id),
      members: this.projects.getMembers(id),
      activities: this.activityService.loadForProject(id),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: ({ project, members, activities }) => {
          this.project.set(project);
          this.members.set(members);
          for (const activity of activities) {
            this.activityService.loadAdvances(activity.id).subscribe({
              error: (error: unknown) =>
                this.error.set(apiErrorMessage(error, 'No se pudieron cargar los avances.')),
            });
          }
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo cargar el proyecto.')),
      });
  }

  memberName(id: number): string {
    return this.members().find((member) => member.id === id)?.nombre ?? 'Integrante';
  }

  status(activity: Activity): string {
    return this.activityService.activityStatus(activity);
  }

  toggleActivityForm(): void {
    this.showActivityForm.update((value) => !value);
  }

  statusClass(activity: Activity): string {
    const status = this.status(activity);
    return status === 'aprobada'
      ? 'status-approved'
      : status === 'en_revision'
        ? 'status-progress'
        : 'status-pending';
  }

  canSubmitAdvance(activity: Activity): boolean {
    return (
      activity.responsable_id === this.auth.user()?.id &&
      this.status(activity) !== 'aprobada' &&
      !(this.activityService.advances()[activity.id] ?? []).some(
        (advance) => advance.estado === 'pendiente',
      )
    );
  }

  pendingAdvances(activity: Activity): Progress[] {
    return (this.activityService.advances()[activity.id] ?? []).filter(
      (advance) => advance.estado === 'pendiente',
    );
  }

  invite(): void {
    if (this.inviteForm.invalid || this.inviting()) {
      this.inviteForm.markAllAsTouched();
      return;
    }
    this.inviteMessage.set('');
    this.inviting.set(true);
    this.projects
      .invite(this.projectId, this.inviteForm.controls.correo.value.trim())
      .pipe(finalize(() => this.inviting.set(false)))
      .subscribe({
        next: () => {
          this.inviteForm.reset();
          this.inviteMessage.set('Invitación enviada. Tu compañero la verá en su panel.');
        },
        error: (error: unknown) =>
          this.inviteMessage.set(apiErrorMessage(error, 'No se pudo enviar la invitación.')),
      });
  }

  createActivity(): void {
    if (this.activityForm.invalid || this.creatingActivity()) {
      this.activityForm.markAllAsTouched();
      return;
    }
    const form = this.activityForm.getRawValue();
    this.creatingActivity.set(true);
    this.activityService
      .create(this.projectId, {
        nombre: form.nombre.trim(),
        descripcion: form.descripcion.trim() || null,
        puntos_acordados: Number(form.puntos_acordados),
        responsable_id: Number(form.responsable_id),
      })
      .pipe(finalize(() => this.creatingActivity.set(false)))
      .subscribe({
        next: (activity) => {
          this.activityService.loadAdvances(activity.id).subscribe({
            error: (error: unknown) =>
              this.error.set(apiErrorMessage(error, 'No se pudieron cargar los avances.')),
          });
          this.activityForm.reset({ nombre: '', descripcion: '', puntos_acordados: 1, responsable_id: '' });
          this.showActivityForm.set(false);
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo crear la actividad.')),
      });
  }

  toggleAdvance(activityId: number): void {
    this.activeAdvanceActivity.set(
      this.activeAdvanceActivity() === activityId ? null : activityId,
    );
    this.advanceForm.reset();
  }

  submitAdvance(activityId: number): void {
    if (this.advanceForm.invalid || this.sendingAdvance()) {
      this.advanceForm.markAllAsTouched();
      return;
    }
    const form = this.advanceForm.getRawValue();
    this.sendingAdvance.set(true);
    this.activityService
      .submitAdvance(activityId, {
        descripcion: form.descripcion.trim(),
        url_evidencia: form.url_evidencia.trim() || null,
      })
      .pipe(finalize(() => this.sendingAdvance.set(false)))
      .subscribe({
        next: () => {
          this.activeAdvanceActivity.set(null);
          this.advanceForm.reset();
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo registrar el avance.')),
      });
  }

  review(
    progress: Progress,
    activityId: number,
    estado: 'aprobado' | 'rechazado',
    comentario: string | null = null,
  ): void {
    this.reviewingAdvance.set(progress.id);
    this.activityService
      .reviewAdvance(progress.id, activityId, estado, comentario)
      .pipe(finalize(() => this.reviewingAdvance.set(null)))
      .subscribe({
        next: () => this.cancelReject(),
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo revisar el avance.')),
      });
  }

  startReject(progress: Progress): void {
    this.rejectingAdvance.set(progress.id);
    this.rejectComment.set('');
    this.rejectError.set('');
  }

  cancelReject(): void {
    this.rejectingAdvance.set(null);
    this.rejectComment.set('');
    this.rejectError.set('');
  }

  confirmReject(progress: Progress, activityId: number): void {
    const comentario = this.rejectComment().trim();
    if (!comentario) {
      this.rejectError.set('Explica qué debe corregir el integrante.');
      return;
    }
    this.review(progress, activityId, 'rechazado', comentario);
  }
}
