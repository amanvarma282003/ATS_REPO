import api from './api';
import { ResumeGenerationResponse } from '../types';

export const resumeService = {
  generateResume: async (data: { job_id?: number; jd_text?: string }): Promise<ResumeGenerationResponse> => {
    const response = await api.post('/resume/generate/', data);
    return response.data;
  },

  downloadResume: async (resumeId: string): Promise<Blob> => {
    const response = await api.get(`/resume/download/${resumeId}/`, {
      responseType: 'blob',
    });
    return response.data;
  },
};
