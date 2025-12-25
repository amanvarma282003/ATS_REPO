import api from './api';
import { LoginResponse, User } from '../types';

export const authService = {
  register: async (data: {
    email: string;
    username: string;
    password: string;
    password_confirm: string;
    role: 'CANDIDATE' | 'RECRUITER';
  }): Promise<User> => {
    const response = await api.post('/auth/register/', data);
    return response.data;
  },

  login: async (email: string, password: string): Promise<LoginResponse> => {
    const response = await api.post('/auth/login/', { email, password });
    if (response.data.tokens.access) {
      localStorage.setItem('access_token', response.data.tokens.access);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  },

  getCurrentUser: (): User | null => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('access_token');
  },
};
