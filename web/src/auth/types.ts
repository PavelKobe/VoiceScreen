export interface User {
  id: number;
  email: string;
  role: string;
  active: boolean;
  client_id: number;
  created_at: string;
}

export interface ClientBrief {
  id: number;
  name: string;
  tariff: string;
  active: boolean;
}

export interface MeResponse {
  user: User;
  client: ClientBrief;
}
