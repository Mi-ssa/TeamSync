import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { LoginComponent } from './features/auth/login.component';
import { RegisterComponent } from './features/auth/register.component';
import { ProjectDetailComponent } from './features/projects/project-detail.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: 'login', component: LoginComponent },
  { path: 'registro', component: RegisterComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'proyectos/:id', component: ProjectDetailComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: 'dashboard' },
];
