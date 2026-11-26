import { provideZonelessChangeDetection, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { Activity } from '../../core/models/activity.model';
import { ActividadService } from '../../core/actividad.service';
import { AuthService } from '../../core/auth.service';
import { ProyectoService } from '../../core/proyecto.service';
import { ProjectDetailComponent } from './project-detail.component';

describe('ProjectDetailComponent progress', () => {
  const activities = signal<Activity[]>([]);

  beforeEach(async () => {
    activities.set([]);
    await TestBed.configureTestingModule({
      imports: [ProjectDetailComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({})) },
        },
        {
          provide: ActividadService,
          useValue: { activities, advances: signal({}) },
        },
        { provide: AuthService, useValue: { user: signal(null) } },
        { provide: ProyectoService, useValue: {} },
      ],
    }).compileComponents();
  });

  it('reports zero progress when there are no activities or points', () => {
    const fixture = TestBed.createComponent(ProjectDetailComponent);
    const component = fixture.componentInstance;

    expect(component.totalPoints()).toBe(0);
    expect(component.approvedPoints()).toBe(0);
    expect(component.overallProgress()).toBe(0);
  });

  it('calculates progress from approved activity points only', () => {
    const fixture = TestBed.createComponent(ProjectDetailComponent);
    const component = fixture.componentInstance;
    activities.set([
      activity(1, 3, 'completada'),
      activity(2, 7, 'pendiente'),
    ]);

    expect(component.totalPoints()).toBe(10);
    expect(component.approvedPoints()).toBe(3);
    expect(component.overallProgress()).toBe(30);
  });
});

function activity(id: number, points: number, estado: Activity['estado']): Activity {
  return {
    id,
    proyecto_id: 1,
    responsable_id: 1,
    nombre: `Actividad ${id}`,
    descripcion: null,
    puntos_acordados: points,
    estado,
    fase: 1,
    votos_emitidos: 0,
    votos_requeridos: 0,
    mi_voto: null,
    creado_en: '',
  };
}
