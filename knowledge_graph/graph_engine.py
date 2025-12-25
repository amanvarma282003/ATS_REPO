import networkx as nx
from typing import Dict, List, Any, Tuple
from candidates.models import CandidateProfile, Project, CandidateSkill, ProjectTool


class KnowledgeGraph:
    """
    Knowledge Graph engine using NetworkX.
    Builds graph representation of candidate data for reasoning.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def build_candidate_graph(self, candidate_profile: CandidateProfile) -> nx.DiGraph:
        """
        Build knowledge graph for a candidate.
        
        Node types:
        - Candidate
        - Project
        - Skill
        - Tool
        - Domain
        - Competency (derived)
        
        Edge types:
        - HAS_PROJECT
        - DEMONSTRATES (Project -> Skill)
        - IMPLEMENTED_USING (Project -> Tool)
        - BELONGS_TO_DOMAIN (Skill -> Domain)
        - MAPS_TO_COMPETENCY (Skill -> Competency)
        """
        self.graph.clear()
        
        # Add candidate node
        candidate_id = f"candidate_{candidate_profile.id}"
        self.graph.add_node(
            candidate_id,
            type='Candidate',
            name=candidate_profile.full_name,
            email=candidate_profile.user.email,
            data=candidate_profile
        )
        
        # Add projects
        for project in candidate_profile.projects.all():
            project_id = f"project_{project.id}"
            self.graph.add_node(
                project_id,
                type='Project',
                title=project.title,
                description=project.description,
                outcomes=project.outcomes,
                data=project
            )
            # Edge: Candidate -> Project
            self.graph.add_edge(
                candidate_id,
                project_id,
                type='HAS_PROJECT',
                weight=1.0
            )
            
            # Add tools used in project
            for project_tool in project.project_tools.all():
                tool = project_tool.tool
                tool_id = f"tool_{tool.id}"
                
                if not self.graph.has_node(tool_id):
                    self.graph.add_node(
                        tool_id,
                        type='Tool',
                        name=tool.name,
                        category=tool.category,
                        data=tool
                    )
                
                # Edge: Project -> Tool
                self.graph.add_edge(
                    project_id,
                    tool_id,
                    type='IMPLEMENTED_USING',
                    weight=1.0
                )
        
        # Add skills
        for candidate_skill in candidate_profile.candidate_skills.all():
            skill = candidate_skill.skill
            skill_id = f"skill_{skill.id}"
            
            if not self.graph.has_node(skill_id):
                self.graph.add_node(
                    skill_id,
                    type='Skill',
                    name=skill.name,
                    category=skill.category,
                    data=skill
                )
            
            # If skill is linked to a project
            if candidate_skill.acquired_from_project:
                project_id = f"project_{candidate_skill.acquired_from_project.id}"
                if self.graph.has_node(project_id):
                    # Edge: Project -> Skill
                    weight = self._calculate_skill_weight(candidate_skill)
                    self.graph.add_edge(
                        project_id,
                        skill_id,
                        type='DEMONSTRATES',
                        weight=weight,
                        proficiency=candidate_skill.proficiency_level,
                        years=float(candidate_skill.years_of_experience or 0)
                    )
            else:
                # Direct edge from candidate to skill
                weight = self._calculate_skill_weight(candidate_skill)
                self.graph.add_edge(
                    candidate_id,
                    skill_id,
                    type='HAS_SKILL',
                    weight=weight,
                    proficiency=candidate_skill.proficiency_level,
                    years=float(candidate_skill.years_of_experience or 0)
                )
        
        return self.graph
    
    def _calculate_skill_weight(self, candidate_skill: CandidateSkill) -> float:
        """
        Calculate weight for skill edge based on proficiency and experience.
        """
        proficiency_weights = {
            'BEGINNER': 0.3,
            'INTERMEDIATE': 0.6,
            'EXPERT': 1.0
        }
        
        base_weight = proficiency_weights.get(
            candidate_skill.proficiency_level,
            0.5
        )
        
        # Boost weight based on years of experience
        years = float(candidate_skill.years_of_experience or 0)
        experience_boost = min(years * 0.1, 0.3)  # Max 0.3 boost
        
        return min(base_weight + experience_boost, 1.0)
    
    def add_jd_competencies(self, jd_data: Dict[str, Any]):
        """
        Add job description competencies to graph.
        Creates competency nodes and links to skills.
        """
        required_competencies = jd_data.get('required_competencies', [])
        optional_competencies = jd_data.get('optional_competencies', [])
        
        jd_id = f"jd_{jd_data.get('id', 'temp')}"
        self.graph.add_node(
            jd_id,
            type='JobDescription',
            title=jd_data.get('title', ''),
            company=jd_data.get('company', ''),
            data=jd_data
        )
        
        # Add required competencies
        for comp in required_competencies:
            comp_id = f"comp_{comp['name'].replace(' ', '_')}"
            if not self.graph.has_node(comp_id):
                self.graph.add_node(
                    comp_id,
                    type='Competency',
                    name=comp['name'],
                    description=comp.get('description', ''),
                    required=True
                )
            self.graph.add_edge(
                jd_id,
                comp_id,
                type='REQUIRES',
                weight=1.0
            )
        
        # Add optional competencies
        for comp in optional_competencies:
            comp_id = f"comp_{comp['name'].replace(' ', '_')}"
            if not self.graph.has_node(comp_id):
                self.graph.add_node(
                    comp_id,
                    type='Competency',
                    name=comp['name'],
                    description=comp.get('description', ''),
                    required=False
                )
            self.graph.add_edge(
                jd_id,
                comp_id,
                type='OPTIONAL',
                weight=0.5
            )
    
    def find_matching_paths(self, jd_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find paths from candidate to competencies required by JD.
        Returns evidence for match explanation.
        """
        self.add_jd_competencies(jd_data)
        
        jd_id = f"jd_{jd_data.get('id', 'temp')}"
        candidate_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Candidate']
        
        if not candidate_nodes:
            return {'matched': [], 'missing': [], 'strength': 0.0}
        
        candidate_id = candidate_nodes[0]
        matched_competencies = []
        missing_competencies = []
        
        # Get all competencies linked to this JD
        competency_nodes = list(self.graph.successors(jd_id))
        
        for comp_node in competency_nodes:
            comp_data = self.graph.nodes[comp_node]
            
            # Try to find path from candidate to competency
            try:
                # Check for path (simplified: through skills)
                skill_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Skill']
                matched = False
                evidence_paths = []
                
                for skill_node in skill_nodes:
                    # Check if there's a path from candidate to this skill
                    if nx.has_path(self.graph, candidate_id, skill_node):
                        # Simple heuristic: check if skill name relates to competency
                        skill_name = self.graph.nodes[skill_node].get('name', '').lower()
                        comp_name = comp_data.get('name', '').lower()
                        
                        if skill_name in comp_name or comp_name in skill_name:
                            matched = True
                            path = nx.shortest_path(self.graph, candidate_id, skill_node)
                            evidence_paths.append({
                                'path': path,
                                'skill': skill_name
                            })
                
                if matched:
                    matched_competencies.append({
                        'competency': comp_data.get('name'),
                        'required': comp_data.get('required', False),
                        'evidence': evidence_paths
                    })
                else:
                    missing_competencies.append({
                        'competency': comp_data.get('name'),
                        'required': comp_data.get('required', False)
                    })
            
            except nx.NetworkXNoPath:
                missing_competencies.append({
                    'competency': comp_data.get('name'),
                    'required': comp_data.get('required', False)
                })
        
        # Calculate match strength
        required_matched = len([c for c in matched_competencies if c['required']])
        required_total = len([c for c in competency_nodes if self.graph.nodes[c].get('required', False)])
        
        strength = required_matched / required_total if required_total > 0 else 0.0
        
        return {
            'matched': matched_competencies,
            'missing': missing_competencies,
            'strength': strength,
            'required_coverage': f"{required_matched}/{required_total}"
        }
    
    def select_resume_content(self, jd_data: Dict[str, Any]) -> Dict[str, List[int]]:
        """
        Select projects and skills to include in resume based on JD.
        Returns IDs of selected content.
        """
        matching_result = self.find_matching_paths(jd_data)
        
        # Extract project and skill IDs from matched paths
        selected_projects = set()
        selected_skills = set()
        
        for match in matching_result['matched']:
            for evidence in match.get('evidence', []):
                path = evidence.get('path', [])
                for node in path:
                    node_type = self.graph.nodes[node].get('type')
                    if node_type == 'Project':
                        project_id = int(node.split('_')[1])
                        selected_projects.add(project_id)
                    elif node_type == 'Skill':
                        skill_id = int(node.split('_')[1])
                        selected_skills.add(skill_id)
        
        return {
            'project_ids': list(selected_projects),
            'skill_ids': list(selected_skills),
            'match_strength': matching_result['strength']
        }
    
    def update_weights_from_feedback(self, feedback_data: Dict[str, Any]):
        """
        Update graph edge weights based on recruiter feedback.
        Positive feedback increases weights, negative decreases.
        """
        action = feedback_data.get('action')
        used_competencies = feedback_data.get('used_competencies', [])
        
        weight_delta = 0.1 if action in ['SHORTLIST', 'INTERVIEW', 'HIRE'] else -0.1
        
        # Update weights of edges related to used competencies
        for comp_name in used_competencies:
            comp_id = f"comp_{comp_name.replace(' ', '_')}"
            if self.graph.has_node(comp_id):
                # Find all edges leading to this competency
                for pred in self.graph.predecessors(comp_id):
                    edge_data = self.graph.get_edge_data(pred, comp_id)
                    if edge_data:
                        current_weight = edge_data.get('weight', 0.5)
                        new_weight = max(0.1, min(1.0, current_weight + weight_delta))
                        self.graph[pred][comp_id]['weight'] = new_weight
                        self.graph[pred][comp_id]['feedback_adjusted'] = True
    
    def export_graph_data(self) -> Dict[str, Any]:
        """
        Export graph as JSON-serializable data.
        """
        return {
            'nodes': [
                {
                    'id': node,
                    'type': data.get('type'),
                    'name': data.get('name', data.get('title', '')),
                    **{k: v for k, v in data.items() if k not in ['data']}
                }
                for node, data in self.graph.nodes(data=True)
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'type': data.get('type'),
                    'weight': data.get('weight', 1.0)
                }
                for u, v, data in self.graph.edges(data=True)
            ]
        }
