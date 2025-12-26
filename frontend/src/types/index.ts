// API Types
export interface User {
  id: number;
  email: string;
  username: string;
  role: 'CANDIDATE' | 'RECRUITER';
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  user: User;
  tokens: {
    access: string;
    refresh: string;
  };
  message: string;
}

export interface CandidateProfile {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  location: string;
  preferred_roles: string[];
  summary?: string;
  linkedin?: string;
  github?: string;
  education?: Education[];
  experience?: Experience[];
  publications?: Publication[];
  awards?: Award[];
  extracurricular?: Extracurricular[];
  patents?: Patent[];
  custom_links?: CustomLink[];
  projects?: Project[];
  created_at: string;
  updated_at: string;
}

export interface Education {
  degree: string;
  institution: string;
  start_year: string;
  end_year: string;
  cgpa?: string;
}

export interface Experience {
  company: string;
  role: string;
  start_date: string;
  end_date: string;
  responsibilities: string[];
  location?: string;
  achievements?: string[];
}

export interface Publication {
  title: string;
  venue: string;
  date: string;
  doi?: string;
  description?: string;
}

export interface Award {
  title: string;
  organization: string;
  level?: string;
  date?: string;
}

export interface Extracurricular {
  role: string;
  organization: string;
  location?: string;
  description: string;
}

export interface Patent {
  title: string;
  patent_number?: string;
  filing_date?: string;
  grant_date?: string;
  description?: string;
  inventors?: string;
}

export interface CustomLink {
  label: string;
  url: string;
  description?: string;
}

export interface Project {
  id: number;
  title: string;
  description: string;
  outcomes: string[];
  created_at: string;
  updated_at: string;
}

export interface Skill {
  id: number;
  name: string;
  category: 'TECHNICAL' | 'SOFT' | 'DOMAIN';
}

export interface CandidateSkill {
  id: number;
  skill: number;
  skill_name?: string;
  proficiency_level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
  years_of_experience: number;
}

export interface JobDescription {
  id: number;
  recruiter: number;
  recruiter_email: string;
  title: string;
  company: string;
  description: string;
  required_competencies: string[];
  status?: 'ACTIVE' | 'CLOSED';
  posted_at: string;
  updated_at: string;
}

export interface MatchExplanation {
  decision: string;
  confidence: number;
  explanation: string;
  strengths: string[];
  gaps: string[];
}

export interface Application {
  id: number;
  candidate: number;
  candidate_info?: {
    id: number;
    email: string;
    full_name: string;
    phone: string;
    location: string;
  };
  job: number;
  job_title: string;
  job_company: string;
  resume_id: string;
  resume_version: any;
  generated_pdf_path: string;
  status: 'PENDING' | 'SHORTLISTED' | 'REJECTED' | 'INTERVIEWED' | 'HIRED';
  match_explanation: MatchExplanation;
  applied_at: string;
  updated_at: string;
}

export interface ResumeGenerationResponse {
  message: string;
  resume_id: string;
  pdf_path: string;
  application_id?: number;
  match_explanation?: any;
  attempt: number;
  display_label: string;
  version: number;
  source: 'JOB' | 'JD_TEXT';
}

export interface ResumeLabelPreview {
  base_label: string;
  display_label: string;
  next_version: number;
}

export interface GeneratedResumeRecord {
  resume_id: string;
  display_label: string;
  version: number;
  pdf_path: string;
  source: 'JOB' | 'JD_TEXT';
  created_at: string;
  job_id?: number;
  jd_title?: string;
  jd_company?: string;
}

export interface ResumeHistoryResponse {
  resumes: GeneratedResumeRecord[];
}

export interface SelectedContentSummary {
  project_ids: number[];
  skill_ids: number[];
  match_strength?: number;
}

export interface CandidateApplicationResponse {
  message: string;
  application_id: number;
  job_id: number;
  resume_id: string;
  has_pdf: boolean;
  match_explanation: MatchExplanation;
  selected_content: SelectedContentSummary;
  resume_source: 'existing' | 'snapshot';
}

export interface CandidateApplicationPreview {
  job_id: number;
  job_title: string;
  match_strength: number;
  selected_projects: number;
  selected_skills: number;
  selected_content: SelectedContentSummary;
}
