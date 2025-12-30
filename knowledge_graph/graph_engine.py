import re

import networkx as nx
import numpy as np
from typing import Any, Dict, List, Tuple, Optional
from candidates.models import CandidateProfile, Project, CandidateSkill
from knowledge_graph.competency_classifier import normalize_competencies
from knowledge_graph.embedding_service import get_embedding_service


class KnowledgeGraph:
    """
    Knowledge Graph engine using NetworkX.
    Builds graph representation of candidate data for reasoning.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.embedding_service = get_embedding_service()
        self.match_threshold = 0.35
        self.max_evidence_per_competency = 3
        self.skill_only_coverage_penalty = 0.7
    
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
        - Experience
        - Education
        - Publication
        - Award
        
        Edge types:
        - HAS_PROJECT
        - DEMONSTRATES (Project -> Skill)
        - IMPLEMENTED_USING (Project -> Tool)
        - BELONGS_TO_DOMAIN (Skill -> Domain)
        - MAPS_TO_COMPETENCY (Skill -> Competency)
        - HAS_EXPERIENCE
        - HAS_EDUCATION
        - HAS_PUBLICATION
        - HAS_AWARD
        """
        self.graph.clear()
        
        # Add candidate node with rich profile data
        candidate_id = f"candidate_{candidate_profile.id}"
        self.graph.add_node(
            candidate_id,
            type='Candidate',
            name=candidate_profile.full_name,
            email=candidate_profile.user.email,
            summary=candidate_profile.summary or '',
            data=candidate_profile
        )
        self.graph.nodes[candidate_id]['embedding_label'] = candidate_profile.full_name
        self._attach_text_embedding(
            candidate_id,
            self._compose_candidate_summary(candidate_profile)
        )
        
        # Add experience nodes (work history)
        experiences = candidate_profile.experience if isinstance(candidate_profile.experience, list) else []
        for idx, exp in enumerate(experiences):
            exp_id = f"experience_{candidate_profile.id}_{idx}"
            responsibilities = exp.get('responsibilities', [])
            responsibilities_text = ' '.join(responsibilities)
            self.graph.add_node(
                exp_id,
                type='Experience',
                company=exp.get('company', ''),
                role=exp.get('role', ''),
                description=responsibilities_text,
                location=exp.get('location', ''),
                data=exp
            )
            self.graph.nodes[exp_id]['embedding_label'] = self._compose_experience_label(exp)
            self._attach_text_embedding(
                exp_id,
                self._compose_experience_text(exp)
            )
            self.graph.add_edge(
                candidate_id,
                exp_id,
                type='HAS_EXPERIENCE',
                weight=1.0
            )
        
        # Add education nodes
        education = candidate_profile.education if isinstance(candidate_profile.education, list) else []
        for idx, edu in enumerate(education):
            edu_id = f"education_{candidate_profile.id}_{idx}"
            self.graph.add_node(
                edu_id,
                type='Education',
                institution=edu.get('institution', ''),
                degree=edu.get('degree', ''),
                field=edu.get('field_of_study', ''),
                data=edu
            )
            self.graph.nodes[edu_id]['embedding_label'] = self._compose_education_label(edu)
            self._attach_text_embedding(
                edu_id,
                self._compose_education_text(edu)
            )
            self.graph.add_edge(
                candidate_id,
                edu_id,
                type='HAS_EDUCATION',
                weight=1.0
            )
        
        # Add publication nodes
        publications = candidate_profile.publications if isinstance(candidate_profile.publications, list) else []
        for idx, pub in enumerate(publications):
            pub_id = f"publication_{candidate_profile.id}_{idx}"
            self.graph.add_node(
                pub_id,
                type='Publication',
                title=pub.get('title', ''),
                venue=pub.get('venue', ''),
                description=pub.get('description', ''),
                data=pub
            )
            self.graph.nodes[pub_id]['embedding_label'] = pub.get('title', '') or f"Publication {idx + 1}"
            self._attach_text_embedding(
                pub_id,
                self._compose_publication_text(pub)
            )
            self.graph.add_edge(
                candidate_id,
                pub_id,
                type='HAS_PUBLICATION',
                weight=1.2  # Publications weighted slightly higher
            )
        
        # Add award nodes
        awards = candidate_profile.awards if isinstance(candidate_profile.awards, list) else []
        for idx, award in enumerate(awards):
            award_id = f"award_{candidate_profile.id}_{idx}"
            self.graph.add_node(
                award_id,
                type='Award',
                title=award.get('title', ''),
                organization=award.get('organization', ''),
                level=award.get('level', ''),
                data=award
            )
            self.graph.nodes[award_id]['embedding_label'] = award.get('title', '') or f"Award {idx + 1}"
            self._attach_text_embedding(
                award_id,
                self._compose_award_text(award)
            )
            self.graph.add_edge(
                candidate_id,
                award_id,
                type='HAS_AWARD',
                weight=1.1  # Awards weighted slightly higher
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
            self.graph.nodes[project_id]['embedding_label'] = project.title
            self._attach_text_embedding(
                project_id,
                self._compose_project_text(project)
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
                self.graph.nodes[skill_id]['embedding_label'] = skill.name
                self._attach_text_embedding(
                    skill_id,
                    self._compose_skill_text(skill)
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

    def _attach_text_embedding(self, node_id: str, text: str, *, as_query: bool = False):
        text = (text or '').strip()
        if not text:
            return
        self.graph.nodes[node_id]['embedding_text'] = text
        embeddings = self.embedding_service.encode([text], as_query=as_query)
        if embeddings:
            self.graph.nodes[node_id]['embedding'] = embeddings[0]

    def _update_competency_metadata(self, comp_id: str, comp: Dict[str, Any]) -> None:
        node = self.graph.nodes[comp_id]
        node['name'] = comp.get('name', node.get('name', ''))
        node['description'] = comp.get('description', node.get('description', ''))
        node['category'] = comp.get('category', node.get('category', 'GENERAL'))
        node['weight'] = float(comp.get('weight') or node.get('weight') or 0.8)
        node['match_threshold'] = float(comp.get('match_threshold') or node.get('match_threshold') or self.match_threshold)
        node['canonical_name'] = comp.get('canonical_name', node.get('canonical_name', node.get('name', '')))
        importance = comp.get('importance') or node.get('importance') or ('REQUIRED' if node.get('required') else 'OPTIONAL')
        node['importance'] = importance.upper()
        node['embedding_label'] = node['name']

    def _get_candidate_evidence_nodes(self, candidate_id: str) -> List[Dict[str, Any]]:
        evidence_types = {
            'Skill': 'skill',
            'Project': 'project',
            'Experience': 'experience',
            'Education': 'education',
            'Publication': 'publication',
            'Award': 'award',
            'Candidate': 'summary'
        }
        evidence_nodes = []
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get('type')
            if node_type not in evidence_types:
                continue
            if node_type == 'Candidate' and node_id != candidate_id:
                continue
            embedding = data.get('embedding')
            text = data.get('embedding_text')
            if embedding is None and text:
                embeddings = self.embedding_service.encode([text])
                if embeddings:
                    embedding = embeddings[0]
                    data['embedding'] = embedding
            if embedding is None:
                continue
            evidence_nodes.append({
                'node_id': node_id,
                'node_type': node_type,
                'match_type': evidence_types[node_type],
                'embedding': embedding,
                'text': text,
                'label': data.get('embedding_label') or data.get('name') or data.get('title')
            })
        return evidence_nodes

    def _find_evidence_matches(
        self,
        comp_embedding: Any,
        evidence_nodes: List[Dict[str, Any]],
        threshold: float
    ) -> Tuple[List[Dict[str, Any]], float]:
        if comp_embedding is None:
            return [], 0.0
        matches = []
        best_similarity = -1.0
        for evidence in evidence_nodes:
            similarity = self._cosine_similarity(comp_embedding, evidence['embedding'])
            if similarity > best_similarity:
                best_similarity = similarity
            if similarity >= threshold:
                matches.append({
                    'node_id': evidence['node_id'],
                    'match_type': evidence['match_type'],
                    'similarity': round(float(similarity), 4),
                    'text': evidence['text'],
                    'label': evidence['label']
                })
        matches.sort(key=lambda item: item['similarity'], reverse=True)
        return matches[:self.max_evidence_per_competency], max(0.0, float(best_similarity))

    def _cosine_similarity(self, vec_a: Any, vec_b: Any) -> float:
        if vec_a is None or vec_b is None:
            return -1.0
        return float(np.dot(vec_a, vec_b))

    def _compose_candidate_summary(self, candidate_profile: CandidateProfile) -> str:
        parts = []
        if candidate_profile.summary:
            parts.append(candidate_profile.summary.strip())
        preferred_roles = candidate_profile.preferred_roles or []
        if preferred_roles:
            parts.append(f"Preferred roles: {', '.join(preferred_roles)}")
        if candidate_profile.location:
            parts.append(f"Location: {candidate_profile.location}")
        if candidate_profile.phone:
            parts.append(f"Phone: {candidate_profile.phone}")
        return '. '.join(parts).strip()

    def _compose_experience_label(self, experience: Dict[str, Any]) -> str:
        role = (experience.get('role') or '').strip()
        company = (experience.get('company') or '').strip()
        if role and company:
            return f"{role} at {company}"
        return role or company or 'Experience'

    def _compose_experience_text(self, experience: Dict[str, Any]) -> str:
        parts = [self._compose_experience_label(experience)]
        location = experience.get('location')
        if location:
            parts.append(f"Location: {location}")
        duration_parts = []
        if experience.get('start_date'):
            duration_parts.append(experience['start_date'])
        if experience.get('end_date'):
            duration_parts.append(experience['end_date'])
        if duration_parts:
            parts.append(' - '.join(duration_parts))
        responsibilities = experience.get('responsibilities') or experience.get('achievements') or []
        if responsibilities:
            parts.append('Responsibilities: ' + '; '.join(responsibilities))
        return '. '.join([p for p in parts if p]).strip()

    def _compose_education_label(self, education: Dict[str, Any]) -> str:
        degree = (education.get('degree') or '').strip()
        institution = (education.get('institution') or '').strip()
        if degree and institution:
            return f"{degree} - {institution}"
        return degree or institution or 'Education'

    def _compose_education_text(self, education: Dict[str, Any]) -> str:
        parts = [self._compose_education_label(education)]
        field = education.get('field_of_study')
        if field:
            parts.append(f"Field: {field}")
        cgpa = education.get('cgpa')
        if cgpa:
            parts.append(f"CGPA: {cgpa}")
        duration_parts = []
        if education.get('start_year'):
            duration_parts.append(str(education['start_year']))
        if education.get('end_year'):
            duration_parts.append(str(education['end_year']))
        if duration_parts:
            parts.append(' - '.join(duration_parts))
        return '. '.join([p for p in parts if p]).strip()

    def _compose_publication_text(self, publication: Dict[str, Any]) -> str:
        parts = [publication.get('title') or 'Publication']
        if publication.get('venue'):
            parts.append(f"Venue: {publication['venue']}")
        if publication.get('description'):
            parts.append(publication['description'])
        if publication.get('doi'):
            parts.append(f"DOI: {publication['doi']}")
        return '. '.join([p for p in parts if p]).strip()

    def _compose_award_text(self, award: Dict[str, Any]) -> str:
        parts = [award.get('title') or 'Award']
        if award.get('organization'):
            parts.append(f"Organization: {award['organization']}")
        if award.get('level'):
            parts.append(f"Level: {award['level']}")
        if award.get('description'):
            parts.append(award['description'])
        return '. '.join([p for p in parts if p]).strip()

    def _compose_project_text(self, project: Project) -> str:
        outcomes = project.outcomes or []
        outcomes_text = f" Outcomes: {'; '.join(outcomes)}" if outcomes else ''
        return f"{project.title}. {project.description or ''}{outcomes_text}".strip()

    def _compose_skill_text(self, skill: Any) -> str:
        category = f" ({skill.category})" if skill.category else ''
        return f"{skill.name}{category}".strip()

    def _compose_competency_text(self, competency: Dict[str, Any]) -> str:
        name = competency.get('name', '')
        description = competency.get('description', '')
        return f"{name}. {description}".strip()
    
    def _format_competency_id(self, name: str) -> str:
        slug = re.sub(r'[^a-z0-9]+', '_', (name or 'competency').lower()).strip('_')
        if not slug:
            slug = 'competency'
        return f"comp_{slug}"

    def _ensure_enriched_competencies(self, entries: List[Dict[str, Any]], importance: str) -> List[Dict[str, Any]]:
        if not entries:
            return []
        needs_enrichment = False
        for entry in entries:
            if not isinstance(entry, dict) or 'match_threshold' not in entry or 'importance' not in entry:
                needs_enrichment = True
                break
        if needs_enrichment:
            return normalize_competencies(entries, importance=importance)
        return entries
    
    def add_jd_competencies(self, jd_data: Dict[str, Any]):
        """
        Add job description competencies to graph.
        Creates competency nodes and links to skills.
        """
        required_competencies = self._ensure_enriched_competencies(
            jd_data.get('required_competencies', []),
            importance='required'
        )
        optional_competencies = self._ensure_enriched_competencies(
            jd_data.get('optional_competencies', []),
            importance='optional'
        )
        
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
            comp_id = self._format_competency_id(comp.get('canonical_name') or comp.get('name', ''))
            if not self.graph.has_node(comp_id):
                self.graph.add_node(
                    comp_id,
                    type='Competency',
                    name=comp.get('name', ''),
                    description=comp.get('description', ''),
                    required=True
                )
            self._update_competency_metadata(comp_id, comp)
            self.graph.nodes[comp_id]['required'] = True
            self._attach_text_embedding(
                comp_id,
                self._compose_competency_text(comp),
                as_query=True
            )
            self.graph.add_edge(
                jd_id,
                comp_id,
                type='REQUIRES',
                weight=float(comp.get('weight') or 1.0)
            )
        
        # Add optional competencies
        for comp in optional_competencies:
            comp_id = self._format_competency_id(comp.get('canonical_name') or comp.get('name', ''))
            if not self.graph.has_node(comp_id):
                self.graph.add_node(
                    comp_id,
                    type='Competency',
                    name=comp.get('name', ''),
                    description=comp.get('description', ''),
                    required=False
                )
            self._update_competency_metadata(comp_id, comp)
            if 'required' not in self.graph.nodes[comp_id]:
                self.graph.nodes[comp_id]['required'] = False
            self._attach_text_embedding(
                comp_id,
                self._compose_competency_text(comp),
                as_query=True
            )
            self.graph.add_edge(
                jd_id,
                comp_id,
                type='OPTIONAL',
                weight=float(comp.get('weight') or 0.5)
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
        total_possible = 0.0
        total_earned = 0.0
        required_total = 0
        required_matched = 0
        required_possible_points = 0.0
        required_earned_points = 0.0
        optional_possible_points = 0.0
        optional_earned_points = 0.0
        
        # Get all competencies linked to this JD
        competency_nodes = list(self.graph.successors(jd_id))
        evidence_nodes = self._get_candidate_evidence_nodes(candidate_id)

        for comp_node in competency_nodes:
            comp_data = self.graph.nodes[comp_node]
            comp_name = comp_data.get('name', '')
            comp_embedding = comp_data.get('embedding')
            if comp_embedding is None:
                comp_text = comp_data.get('embedding_text') or comp_name
                self._attach_text_embedding(comp_node, comp_text, as_query=True)
                comp_embedding = self.graph.nodes[comp_node].get('embedding')

            match_threshold = float(comp_data.get('match_threshold') or self.match_threshold)
            threshold = max(0.05, match_threshold)
            evidence, best_similarity = self._find_evidence_matches(comp_embedding, evidence_nodes, threshold)
            importance = (comp_data.get('importance') or ('REQUIRED' if comp_data.get('required', False) else 'OPTIONAL')).upper()
            is_required = importance == 'REQUIRED'
            comp_weight = float(comp_data.get('weight') or 0.8)
            importance_multiplier = 1.0 if is_required else 0.6
            max_points = comp_weight * importance_multiplier
            total_possible += max_points
            if is_required:
                required_total += 1
                required_possible_points += max_points
            else:
                optional_possible_points += max_points

            similarity_clamped = max(0.0, min(1.0, best_similarity))
            coverage_ratio = 0.0
            if similarity_clamped > 0 and threshold > 0:
                coverage_ratio = min(1.0, similarity_clamped / threshold)

            penalty_multiplier = 1.0
            if coverage_ratio > 0 and evidence and all(ev['match_type'] == 'skill' for ev in evidence):
                penalty_multiplier = self.skill_only_coverage_penalty
                coverage_ratio *= penalty_multiplier

            earned_points = max_points * coverage_ratio
            total_earned += earned_points
            if is_required:
                required_earned_points += earned_points
            else:
                optional_earned_points += earned_points

            status = 'matched' if similarity_clamped >= threshold else ('partial' if similarity_clamped > 0 else 'missing')
            if is_required and status == 'matched':
                required_matched += 1

            comp_payload = {
                'competency': comp_name,
                'canonical_name': comp_data.get('canonical_name', comp_name),
                'required': is_required,
                'importance': importance,
                'category': comp_data.get('category', 'GENERAL'),
                'weight': round(comp_weight, 3),
                'importance_weight': round(importance_multiplier, 3),
                'match_threshold': round(threshold, 4),
                'best_similarity': round(similarity_clamped, 4),
                'coverage': round(coverage_ratio, 4),
                'coverage_penalty': round(penalty_multiplier, 3),
                'status': status,
                'evidence': evidence
            }

            if status == 'matched':
                matched_competencies.append(comp_payload)
            else:
                missing_competencies.append(comp_payload)
        
        strength = total_earned / total_possible if total_possible > 0 else 0.0
        required_weighted = required_earned_points / required_possible_points if required_possible_points > 0 else 0.0
        optional_weighted = optional_earned_points / optional_possible_points if optional_possible_points > 0 else 0.0
        
        return {
            'matched': matched_competencies,
            'missing': missing_competencies,
            'strength': strength,
            'required_coverage': f"{required_matched}/{required_total}",
            'similarity_threshold': self.match_threshold,
            'coverage_summary': {
                'overall_weighted': round(strength, 4),
                'required_weighted': round(required_weighted, 4),
                'optional_weighted': round(optional_weighted, 4),
                'total_possible_points': round(total_possible, 3)
            }
        }
    
    def select_resume_content(
        self,
        jd_data: Dict[str, Any],
        *,
        matching_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Select projects, skills, experiences, and education to include in resume based on JD.
        Returns IDs/indices of selected content.
        """
        if matching_result is None:
            matching_result = self.find_matching_paths(jd_data)
        
        # Extract all content IDs from matched paths
        selected_projects = set()
        selected_skills = set()
        selected_experiences = set()
        selected_education = set()
        selected_publications = set()
        selected_awards = set()
        
        for match in matching_result['matched']:
            for evidence in match.get('evidence', []):
                node_reference = evidence.get('node_id')
                nodes_to_process = []
                if node_reference and self.graph.has_node(node_reference):
                    nodes_to_process = [node_reference]
                else:
                    nodes_to_process = evidence.get('path', [])

                for node in nodes_to_process:
                    if not self.graph.has_node(node):
                        continue
                    node_type = self.graph.nodes[node].get('type')
                    if node_type == 'Project':
                        project_id = int(node.split('_')[1])
                        selected_projects.add(project_id)
                    elif node_type == 'Skill':
                        skill_id = int(node.split('_')[1])
                        selected_skills.add(skill_id)
                    elif node_type == 'Experience':
                        parts = node.split('_')
                        exp_idx = int(parts[-1])
                        selected_experiences.add(exp_idx)
                    elif node_type == 'Education':
                        parts = node.split('_')
                        edu_idx = int(parts[-1])
                        selected_education.add(edu_idx)
                    elif node_type == 'Publication':
                        parts = node.split('_')
                        pub_idx = int(parts[-1])
                        selected_publications.add(pub_idx)
                    elif node_type == 'Award':
                        parts = node.split('_')
                        award_idx = int(parts[-1])
                        selected_awards.add(award_idx)
        
        # ALWAYS include ALL projects - candidate's work should be fully evaluated
        all_projects = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Project']
        for project_node in all_projects:
            project_id = int(project_node.split('_')[1])
            selected_projects.add(project_id)
        
        # ALWAYS include ALL experiences - work history is fundamental to evaluation
        all_experiences = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Experience']
        for exp_node in all_experiences:
            parts = exp_node.split('_')
            exp_idx = int(parts[-1])
            selected_experiences.add(exp_idx)
        
        # ALWAYS include ALL education - academic background is core to candidate assessment
        all_education = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Education']
        for edu_node in all_education:
            parts = edu_node.split('_')
            edu_idx = int(parts[-1])
            selected_education.add(edu_idx)
        
        # ALWAYS include ALL publications - research contributions must be evaluated
        all_publications = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Publication']
        for pub_node in all_publications:
            parts = pub_node.split('_')
            pub_idx = int(parts[-1])
            selected_publications.add(pub_idx)
        
        # ALWAYS include ALL awards - achievements are part of complete evaluation
        all_awards = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Award']
        for award_node in all_awards:
            parts = award_node.split('_')
            award_idx = int(parts[-1])
            selected_awards.add(award_idx)

        # ALWAYS include ALL skills - ensures semantic profile coverage
        all_skills = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'Skill']
        for skill_node in all_skills:
            skill_id = int(skill_node.split('_')[1])
            selected_skills.add(skill_id)
        
        match_strength = matching_result['strength']
        
        return {
            'project_ids': list(selected_projects),
            'skill_ids': list(selected_skills),
            'experience_indices': list(selected_experiences),
            'education_indices': list(selected_education),
            'publication_indices': list(selected_publications),
            'award_indices': list(selected_awards),
            'match_strength': match_strength,
            'coverage_summary': matching_result.get('coverage_summary', {}),
            'required_coverage': matching_result.get('required_coverage'),
            'matched_competencies': matching_result.get('matched', []),
            'missing_competencies': matching_result.get('missing', [])
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
