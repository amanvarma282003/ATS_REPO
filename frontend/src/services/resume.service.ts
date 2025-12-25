import api from './api';
import {
  ResumeGenerationResponse,
  ResumeLabelPreview,
  ResumeHistoryResponse,
} from '../types';

export const resumeService = {
  generateResume: async (data: { job_id?: number; jd_text?: string }): Promise<ResumeGenerationResponse> => {
    const response = await api.post('/resume/generate/', data);
    return response.data;
  },

  previewLabel: async (data: { job_id?: number; jd_text?: string }): Promise<ResumeLabelPreview> => {
    const response = await api.post('/resume/label/', data);
    return response.data;
  },

  downloadResume: async (resumeId: string): Promise<Blob> => {
    const response = await api.get(`/resume/download/${resumeId}/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  getResumeHistory: async (): Promise<ResumeHistoryResponse> => {
    const response = await api.get('/resume/history/');
    return response.data;
  },
};
