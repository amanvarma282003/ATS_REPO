import api from './api';
import { JobDescription, Application } from '../types';

export const recruiterService = {
  getJobs: async (): Promise<JobDescription[]> => {
    const response = await api.get('/recruiter/jobs/');
    return response.data;
  },

  createJob: async (data: Omit<JobDescription, 'id' | 'recruiter' | 'recruiter_email' | 'posted_at' | 'updated_at'>): Promise<JobDescription> => {
    const response = await api.post('/recruiter/jobs/', data);
    return response.data;
  },

  getApplications: async (jobId?: number): Promise<Application[]> => {
    const url = jobId ? `/recruiter/applications/?job_id=${jobId}` : '/recruiter/applications/';
    const response = await api.get(url);
    return response.data;
  },

  getApplication: async (id: number): Promise<Application> => {
    const response = await api.get(`/recruiter/applications/${id}/`);
    return response.data;
  },

  submitFeedback: async (data: {
    application: number;
    action: 'SHORTLIST' | 'REJECT' | 'INTERVIEW' | 'HIRE';
    reason?: string;
  }) => {
    const response = await api.post('/recruiter/feedback/', data);
    return response.data;
  },
};
