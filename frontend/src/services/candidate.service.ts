import api from './api';
import { CandidateProfile, Project, Skill, CandidateSkill } from '../types';

export const candidateService = {
  getProfile: async (): Promise<CandidateProfile> => {
    const response = await api.get('/candidate/profile/');
    return response.data;
  },

  updateProfile: async (data: Partial<CandidateProfile>): Promise<CandidateProfile> => {
    const response = await api.put('/candidate/profile/', data);
    return response.data;
  },

  uploadResume: async (resumeText: string) => {
    const response = await api.post('/candidate/profile/upload_resume/', {
      resume_text: resumeText,
    });
    return response.data;
  },

  getProjects: async (): Promise<Project[]> => {
    const response = await api.get('/candidate/projects/');
    return response.data;
  },

  createProject: async (data: Omit<Project, 'id' | 'created_at' | 'updated_at'>): Promise<Project> => {
    const response = await api.post('/candidate/projects/', data);
    return response.data;
  },

  deleteProject: async (id: number): Promise<void> => {
    await api.delete(`/candidate/projects/${id}/`);
  },

  getSkills: async (): Promise<Skill[]> => {
    const response = await api.get('/candidate/skills/');
    return response.data;
  },

  createSkill: async (data: { name: string; category: string }): Promise<Skill> => {
    const response = await api.post('/candidate/skills/', data);
    return response.data;
  },

  getMySkills: async (): Promise<CandidateSkill[]> => {
    const response = await api.get('/candidate/my-skills/');
    return response.data;
  },

  addMySkill: async (data: {
    skill: number;
    proficiency_level: string;
    years_of_experience: number;
  }): Promise<CandidateSkill> => {
    const response = await api.post('/candidate/my-skills/', data);
    return response.data;
  },

  deleteMySkill: async (id: number): Promise<void> => {
    await api.delete(`/candidate/my-skills/${id}/`);
  },
};
