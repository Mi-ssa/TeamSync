import { Component, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { finalize, forkJoin, of } from 'rxjs';
import { apiErrorMessage } from '../../core/api-error';
import { AuthService } from '../../core/auth.service';
import { FaseService } from '../../core/fase.service';
import {
  ContributionSummary,
  Declaration,
  PeerEvaluationInput,
} from '../../core/models/contribution.model';
import { Project, ProjectMember } from '../../core/models/project.model';

type Confirmation = 'cerrar' | 'concluir' | null;

@Component({
  selector: 'app-contribution-panel',
  standalone: true,
  imports: [DatePipe, FormsModule],
  templateUrl: './contribution-panel.component.html',
})
export class ContributionPanelComponent {
  private readonly fases = inject(FaseService);
  readonly auth = inject(AuthService);

  readonly project = input.required<Project>();
  readonly members = input.required<ProjectMember[]>();
  readonly isLeader = input(false);
  /** El padre lo incrementa cuando cambian actividades o avances. */
  readonly refresh = input(0);
  readonly projectChanged = output<Project>();

  readonly summary = signal<ContributionSummary | null>(null);
  readonly declaration = signal<Declaration | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly message = signal('');
  readonly saving = signal<number | null>(null);
  readonly confirming = signal<Confirmation>(null);
  readonly working = signal(false);
  readonly signing = signal(false);
  drafts: Record<number, PeerEvaluationInput> = {};

  readonly peers = computed(() =>
    this.members().filter((member) => member.id !== this.auth.user()?.id),
  );
  readonly concluded = computed(() => this.project().estado === 'concluido');
  readonly checkInDone = computed(() => {
    const done = new Set((this.summary()?.mis_evaluaciones ?? []).map((e) => e.evaluado_id));
    return this.peers().filter((peer) => done.has(peer.id)).length;
  });
  readonly scale = [1, 2, 3, 4, 5];

  constructor() {
    effect(() => {
      this.project();
      this.refresh();
      untracked(() => this.load());
    });
  }

  load(): void {
    const project = this.project();
    this.loading.set(true);
    this.error.set('');
    forkJoin({
      summary: this.fases.contribution(project.id),
      declaration: project.estado === 'concluido' ? this.fases.declaration(project.id) : of(null),
    })
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: ({ summary, declaration }) => {
          this.summary.set(summary);
          this.declaration.set(declaration);
          this.buildDrafts(summary);
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo cargar la contribución.')),
      });
  }

  evaluated(memberId: number): boolean {
    return (this.summary()?.mis_evaluaciones ?? []).some((e) => e.evaluado_id === memberId);
  }

  saveEvaluation(memberId: number): void {
    const draft = this.drafts[memberId];
    if (!draft || this.saving()) {
      return;
    }
    this.saving.set(memberId);
    this.message.set('');
    this.fases
      .evaluate(this.project().id, {
        ...draft,
        comunicacion: Number(draft.comunicacion),
        calidad: Number(draft.calidad),
        compromiso: Number(draft.compromiso),
        comentario: draft.comentario?.trim() || null,
      })
      .pipe(finalize(() => this.saving.set(null)))
      .subscribe({
        next: () => {
          this.message.set('Check-in guardado.');
          this.load();
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo guardar la evaluación.')),
      });
  }

  confirm(action: Exclude<Confirmation, null>): void {
    this.confirming.set(action);
    this.error.set('');
  }

  runConfirmed(): void {
    const action = this.confirming();
    if (!action || this.working()) {
      return;
    }
    const request =
      action === 'cerrar'
        ? this.fases.closePhase(this.project().id)
        : this.fases.conclude(this.project().id);
    this.working.set(true);
    request
      .pipe(
        finalize(() => {
          this.working.set(false);
          this.confirming.set(null);
        }),
      )
      .subscribe({
        next: (project) => {
          this.message.set(
            action === 'cerrar'
              ? `Fase cerrada. Ahora trabajan en la fase ${project.fase_actual}.`
              : 'Proyecto concluido. Ya pueden firmar la declaración de contribución.',
          );
          this.projectChanged.emit(project);
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo completar la acción.')),
      });
  }

  sign(): void {
    if (this.signing()) {
      return;
    }
    this.signing.set(true);
    this.fases
      .sign(this.project().id)
      .pipe(finalize(() => this.signing.set(false)))
      .subscribe({
        next: (declaration) => {
          this.declaration.set(declaration);
          this.message.set('Firmaste la declaración de contribución.');
        },
        error: (error: unknown) =>
          this.error.set(apiErrorMessage(error, 'No se pudo firmar la declaración.')),
      });
  }

  printDeclaration(): void {
    window.print();
  }

  private buildDrafts(summary: ContributionSummary): void {
    const drafts: Record<number, PeerEvaluationInput> = {};
    for (const peer of this.peers()) {
      const previous = summary.mis_evaluaciones.find((e) => e.evaluado_id === peer.id);
      drafts[peer.id] = {
        evaluado_id: peer.id,
        comunicacion: previous?.comunicacion ?? 3,
        calidad: previous?.calidad ?? 3,
        compromiso: previous?.compromiso ?? 3,
        confirma_aporte: previous?.confirma_aporte ?? true,
        comentario: previous?.comentario ?? '',
      };
    }
    this.drafts = drafts;
  }
}
