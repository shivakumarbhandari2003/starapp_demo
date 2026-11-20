"""
Bands and taxonomy service layer.
"""
from typing import List, Dict, Any
from backend.app.features.bands.repository import BandsRepository

DEFAULT_TAXONOMY = {
    "powers": ["Tech", "Business", "Leadership", "Design"],
    "capabilities": {
        "Tech": ["Data & Machine", "Cloud & Infra", "Frontend Systems", "Core Engineering"],
        "Business": ["Strategy & Growth", "Product Lifecycle", "Market Operations"],
        "Leadership": ["Team Architecture", "Mentorship", "Engineering Delivery"],
        "Design": ["Systems Design", "User Experience", "Interaction Systems"],
    },
    "skills": {
        "Data & Machine": ["Hardware", "Model Optimization", "Deep Learning", "Data Pipelines"],
        "Cloud & Infra": ["Kubernetes", "Observability", "Edge Networks", "Security Hardening"],
        "Frontend Systems": ["Micro-Frontends", "Web Performance", "State Architecture", "Canvas Systems"],
        "Core Engineering": ["Distributed Systems", "Concurrency", "Database Internals", "Algorithm Design"],
        "Strategy & Growth": ["Product Roadmapping", "Metrics & OKRs", "Competitive Analysis"],
        "Product Lifecycle": ["Agile Delivery", "Stakeholder Alignment", "Release Engineering"],
        "Market Operations": ["Unit Economics", "GTM Execution", "Client Strategy"],
        "Team Architecture": ["Talent Density", "Culture Scaling", "Hiring Rubrics"],
        "Mentorship": ["Apprenticeship", "Code Review Excellence", "Technical Writing"],
        "Engineering Delivery": ["Incident Response", "Tech Debt Management", "Architecture RFCs"],
        "Systems Design": ["High-Load Arch", "Event-Driven Arch", "Fault Tolerance"],
        "User Experience": ["Accessibility (a11y)", "Design Systems", "Usability Testing"],
        "Interaction Systems": ["Micro-Interactions", "Motion UX", "Information Hierarchy"],
    }
}


class BandsService:
    def __init__(self, repo: BandsRepository):
        self.repo = repo

    def get_bands(self) -> List[Dict[str, Any]]:
        return self.repo.list_bands()

    def get_taxonomy(self) -> Dict[str, Any]:
        # Merge default taxonomy with custom database additions
        custom_caps = self.repo.get_custom_capabilities()
        custom_skills = self.repo.get_custom_skills()
        
        taxonomy = {
            "powers": list(DEFAULT_TAXONOMY["powers"]),
            "capabilities": {k: list(v) for k, v in DEFAULT_TAXONOMY["capabilities"].items()},
            "skills": {k: list(v) for k, v in DEFAULT_TAXONOMY["skills"].items()}
        }
        
        for cap in custom_caps:
            if cap not in taxonomy["capabilities"]["Tech"]:
                taxonomy["capabilities"]["Tech"].append(cap)
            if cap not in taxonomy["skills"]:
                taxonomy["skills"][cap] = []

        for skill_entry in custom_skills:
            cap_name = skill_entry.get("capability_name") or "Data & Machine"
            skill_name = skill_entry.get("name")
            if cap_name in taxonomy["skills"]:
                if skill_name not in taxonomy["skills"][cap_name]:
                    taxonomy["skills"][cap_name].append(skill_name)
            else:
                taxonomy["skills"][cap_name] = [skill_name]

        return taxonomy

    def add_capability(self, name: str, user_id: str) -> bool:
        return self.repo.add_custom_capability(name, user_id)

    def add_skill(self, name: str, capability_name: str, user_id: str) -> bool:
        return self.repo.add_custom_skill(name, capability_name, user_id)
