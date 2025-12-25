import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidate.service';
import { CandidateProfile, Project, CandidateSkill } from '../../types';
import './CandidateDashboard.css';

const CandidateDashboard: React.FC = () => {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [skills, setSkills] = useState<CandidateSkill[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [profileData, projectsData, skillsData] = await Promise.all([
        candidateService.getProfile(),
        candidateService.getProjects(),
        candidateService.getMySkills(),
      ]);
      setProfile(profileData);
      setProjects(projectsData);
      setSkills(skillsData);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="dashboard-container">Loading...</div>;
  }

  return (
    <div className="dashboard-container">
      <h1>Candidate Dashboard</h1>
      
      <div className="dashboard-section">
        <h2>Profile Summary</h2>
        <div className="profile-card">
          <p><strong>Name:</strong> {profile?.full_name || 'Not set'}</p>
          <p><strong>Email:</strong> {profile?.email}</p>
          <p><strong>Phone:</strong> {profile?.phone || 'Not set'}</p>
          <p><strong>Location:</strong> {profile?.location || 'Not set'}</p>
        </div>
      </div>

      <div className="dashboard-section">
        <h2>Projects ({projects.length})</h2>
        {projects.length === 0 ? (
          <p>No projects added yet.</p>
        ) : (
          <div className="projects-grid">
            {projects.map((project) => (
              <div key={project.id} className="project-card">
                <h3>{project.title}</h3>
                <p>{project.description}</p>
                {project.outcomes.length > 0 && (
                  <ul>
                    {project.outcomes.map((outcome, idx) => (
                      <li key={idx}>{outcome}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="dashboard-section">
        <h2>Skills ({skills.length})</h2>
        {skills.length === 0 ? (
          <p>No skills added yet.</p>
        ) : (
          <div className="skills-list">
            {skills.map((skill) => (
              <div key={skill.id} className="skill-badge">
                {skill.skill_name || `Skill ${skill.skill}`} - {skill.proficiency_level} ({skill.years_of_experience}y)
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="dashboard-actions">
        <Link to="/candidate/profile" className="btn-primary">Edit Profile</Link>
        <Link to="/candidate/generate-resume" className="btn-primary">Generate Resume</Link>
      </div>
    </div>
  );
};

export default CandidateDashboard;
