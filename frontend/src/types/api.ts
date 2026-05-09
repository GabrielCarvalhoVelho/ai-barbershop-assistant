// Mirrors Pydantic schemas in backend/app/modules/{auth,chat,appointments}/schemas.py
// and enums in backend/app/models/enums.py. Update here when backend contracts change.

export type IsoDateTime = string;

// (string & {}) keeps autocomplete for known codes without closing the union.
// 'NETWORK' is a client-side sentinel produced by mapError when there is no response.
export type ErrorCode =
  | 'AUTH_001'
  | 'AUTH_002'
  | 'AUTH_003'
  | 'AUTH_004'
  | 'CHAT_001'
  | 'APT_001'
  | 'USR_001'
  | 'RES_001'
  | 'RATE_001'
  | 'VAL_001'
  | 'DB_001'
  | 'DB_002'
  | 'DB_003'
  | 'APP_000'
  | 'NETWORK'
  | (string & {});

export type ErrorDetail = {
  code: ErrorCode;
  message: string;
  field: string | null;
  details: string[] | null;
};

export type ApiSuccess<T> = {
  success: true;
  timestamp: IsoDateTime;
  data: T;
};

export type ApiError = {
  success: false;
  timestamp: IsoDateTime;
  request_id: string | null;
  error: ErrorDetail;
};

export type Pagination = {
  limit: number;
  offset: number;
  total: number;
};

export type UserRole = 'customer' | 'admin';
export type MessageSender = 'user' | 'bot';
export type ConversationStatus = 'active' | 'closed';
export type AppointmentStatus =
  | 'scheduled'
  | 'confirmed'
  | 'cancelled'
  | 'completed';

export type LoginRequest = {
  phone: string;
  password: string;
};

export type RegisterRequest = {
  phone: string;
  password: string;
  name: string;
  email: string | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type UserMeResponse = {
  id: number;
  name: string;
  email: string | null;
  phone: string;
  role: UserRole;
  company_id: number;
};

export type ChatRequest = {
  message: string;
  conversation_id: number | null;
};

export type ChatResponse = {
  response: string;
  conversation_id: number;
};

export type Message = {
  id: number;
  sender: MessageSender;
  content: string;
  created_at: IsoDateTime;
  // Client-side only: marca msg otimista que falhou ao enviar; nunca vem do backend.
  failed?: boolean;
};

export type ConversationSummary = {
  id: number;
  user_id: number;
  company_id: number;
  status: ConversationStatus;
  started_at: IsoDateTime;
  ended_at: IsoDateTime | null;
};

export type Conversation = ConversationSummary & {
  message_count: number;
};

export type ConversationDetail = {
  id: number;
  status: ConversationStatus;
  started_at: IsoDateTime;
  ended_at: IsoDateTime | null;
  messages: Message[];
};

export type ConversationMessages = {
  conversation_id: number;
  messages: Message[];
  pagination: Pagination;
};

export type ListMessagesQuery = {
  limit?: number;
  offset?: number;
};

export type Appointment = {
  id: number;
  user_id: number;
  company_id: number;
  service: string;
  scheduled_at: IsoDateTime;
  duration_minutes: number;
  status: AppointmentStatus;
  created_at: IsoDateTime;
  updated_at: IsoDateTime | null;
};

export type AppointmentList = {
  appointments: Appointment[];
  pagination: Pagination;
};

export type ListAppointmentsQuery = {
  limit?: number;
  offset?: number;
};
