export interface User {
  id: number;
  nombre: string;
  correo: string;
  es_admin?: boolean;
  activo?: boolean;
}

export interface RegisterRequest {
  nombre: string;
  correo: string;
  contrasena: string;
}

export interface LoginRequest {
  correo: string;
  contrasena: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
