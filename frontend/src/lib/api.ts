import axios from 'axios';

import type { AuthProfile } from '../types/auth';
import { supabase } from './supabase';

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function fetchCurrentProfile(): Promise<AuthProfile> {
  const { data } = await api.get<AuthProfile>('/auth/me');
  return data;
}
