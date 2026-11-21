"""
Gemini integration router and server-side client.
Keeps Gemini API Key strictly server-side without exposing it to the browser.
"""
import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from backend.app.core.config import GEMINI_API_KEY
from backend.app.core.dependencies import get_current_user, get_current_user_optional

router = APIRouter(prefix="/integrations/gemini", tags=["Gemini AI Integration"])


class GenerateBadgeRequest(BaseModel):
    band: str = "B1"
    power: str = "Tech"
    capability: str = "Data & Machine"
    skill: str = "Hardware"
    outcome_sentence: Optional[str] = ""


class MentorChatRequest(BaseModel):
    message: str
    badge_title: Optional[str] = "Engineering Badge"
    context: Optional[str] = ""


def generate_fallback_badge(band: str, power: str, capability: str, skill: str, outcome_sentence: str) -> Dict[str, Any]:
    """High-quality deterministic fallback curriculum matching StarApp standards."""
    title = f"{skill} Foundations" if band in ("B1", "B2") else (f"{skill} Architecture" if band in ("B3", "B4") else f"{skill} Mastery")
    formatted_outcome = outcome_sentence.strip() if outcome_sentence else f"Identify core {skill.lower()} components and evaluate their primary system roles"
    if not formatted_outcome.startswith("Can "):
        formatted_outcome = "Can " + formatted_outcome[0].lower() + formatted_outcome[1:]
    if not formatted_outcome.endswith("."):
        formatted_outcome += "."

    outcomes = [
        formatted_outcome,
        f"Can analyze how {skill.lower()} architectures impact system performance, throughput, and operational resilience.",
        f"Can design end-to-end specifications meeting Band {band} engineering standards for {capability}.",
        f"Can implement automated telemetry and robust verification routines ensuring zero-regression delivery."
    ]

    learning_topics = [
        {"title": f"1. {skill} Core Fundamentals", "description": f"Essential mechanics, system interfaces, and industry paradigms for {skill.lower()}."},
        {"title": f"2. {skill} Architecture & Design Patterns", "description": f"High-availability patterns, component boundaries, and fault-tolerance for {capability}."},
        {"title": f"3. {skill} Integration & Subsystems", "description": f"Connecting {skill.lower()} components across distributed cloud and on-premise infrastructure."},
        {"title": f"4. {skill} Telemetry & Observability", "description": f"Monitoring latency, error rates, throughput benchmarks, and resource utilization for {skill.lower()}."},
        {"title": f"5. {skill} Optimization & Failure Modes", "description": f"Identifying performance bottlenecks, thermal/memory limits, and recovery strategies for {skill.lower()}."},
        {"title": f"6. {skill} Verification & Governance", "description": f"Enforcing operational governance, security controls, and test harnesses for {skill.lower()}."}
    ]

    topics_bullets = "\n".join([f"- {t['title']}: {t['description']}" for t in learning_topics])
    outcomes_semicolon = "; ".join(outcomes)

    practice_prompt = (
        f"I'm working toward the \"{title}\" badge ({skill} / {capability} / {power}) in Band {band}.\n"
        f"I want to practice the following topics for this badge:\n"
        f"{topics_bullets}\n\n"
        f"By the end I need to be able to: {outcomes_semicolon}\n\n"
        f"Design one small, hands-on practice project that lets me demonstrate all of the topics and outcomes above together. "
        f"Include a clear task description, any starting constraints or inputs I should assume, and what a finished/successful result looks like."
    )

    resources_prompt = (
        f"I'm working toward the \"{title}\" badge ({skill} / {capability} / {power}) in Band {band}.\n"
        f"I need free, current, high-quality learning resources (official docs, free courses, tutorials, videos) that help me learn:\n"
        f"{topics_bullets}\n\n"
        f"By the end I need to be able to: {outcomes_semicolon}\n\n"
        f"Please suggest specific free resources for each topic above (prefer official docs, free interactive tutorials, and reputable free video/blog content over paid courses), "
        f"and suggest one small hands-on project that lets me demonstrate all of the topics together."
    )

    project_requirements = (
        f"Deliver an end-to-end {skill.lower()} implementation accompanied by an architecture document "
        f"addressing performance, error handling, and a 15-minute presentation addressing all 5 rubric criteria."
    )

    return {
        "id": f"badge_{band.lower()}_{skill.lower().replace(' ', '_').replace('-', '_')}",
        "code": f"{band}-{skill[:3].upper()}-01",
        "title": title,
        "description": f"{band} badge specializing in {skill} under the {capability} capability ({power} domain). {outcome_sentence or ''}".strip(),
        "target_band": band,
        "power": power,
        "capability": capability,
        "skill": skill,
        "outcomes": outcomes,
        "learning_topics": learning_topics,
        "practice_prompt": practice_prompt,
        "resources_prompt": resources_prompt,
        "practice_project": {
            "intro": "Want some hands-on practice? Use this prompt to generate a practice project.",
            "prompt": practice_prompt,
            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
        },
        "learning_resources": {
            "intro": "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
            "prompt": resources_prompt,
            "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
        },
        "project_requirements": project_requirements
    }


@router.post("/generate-badge")
async def generate_badge(req: GenerateBadgeRequest, user=Depends(get_current_user_optional)):
    """Generate badge content securely via Gemini API, with fallback on network/quota issues."""
    api_key = GEMINI_API_KEY
    if not api_key:
        return {
            "success": True,
            "badge": generate_fallback_badge(req.band, req.power, req.capability, req.skill, req.outcome_sentence or ""),
            "mode": "deterministic_fallback"
        }

    prompt = f"""You are an expert curriculum architect for engineering badges.
Create a detailed, high-quality badge for:
- Band: {req.band}
- Power: {req.power}
- Capability: {req.capability}
- Skill: {req.skill}
- Outcome Sentence: "{req.outcome_sentence}"

Return ONLY valid JSON with this exact schema:
{{
  "title": "{req.skill} Foundations",
  "description": "Foundational badge covering core {req.skill.lower()} concepts...",
  "outcomes": [
    "Can identify ...",
    "Can analyze ...",
    "Can design ...",
    "Can implement ..."
  ],
  "learning_topics": [
    {{"title": "1. Core Fundamentals", "description": "..."}},
    {{"title": "2. Architecture & Design Patterns", "description": "..."}},
    {{"title": "3. Subsystems & Integration", "description": "..."}},
    {{"title": "4. Telemetry & Observability", "description": "..."}},
    {{"title": "5. Optimization & Resiliency", "description": "..."}},
    {{"title": "6. Verification & Governance", "description": "..."}}
  ],
  "practice_prompt": "I'm working toward the \\"{req.skill} Foundations\\" badge ({req.skill} / {req.capability} / {req.power}) in Band {req.band}.\\nI want to practice the following topics for this badge:\\n...\\n\\nBy the end I need to be able to: ...\\n\\nDesign one small, hands-on practice project that lets me demonstrate all of the topics and outcomes above together. Include a clear task description, starting constraints, and what a finished result looks like.",
  "resources_prompt": "I'm working toward the \\"{req.skill} Foundations\\" badge ({req.skill} / {req.capability} / {req.power}) in Band {req.band}.\\nI need free, current, high-quality learning resources (official docs, free courses, tutorials, videos) that help me learn:\\n...\\n\\nBy the end I need to be able to: ...\\n\\nPlease suggest specific free resources for each topic above, and suggest one small hands-on project that lets me demonstrate all of the topics together.",
  "project_requirements": "..."
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload_data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024}
    }

    try:
        req_obj = urllib.request.Request(
            url,
            data=json.dumps(payload_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_obj, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean possible markdown fence
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            parsed = json.loads(text.strip())

            # Ensure complete rich content for practice project and learning resources
            title = parsed.get("title") or f"{req.skill} Foundations"
            outcomes = parsed.get("outcomes") or [req.outcome_sentence or f"Can architect {req.skill} systems."]
            topics = parsed.get("learning_topics") or []
            topics_bullets = "\n".join([f"- {t.get('title', '')}: {t.get('description', '')}" for t in topics]) if topics else f"- {req.skill} Core Principles"
            outcomes_semicolon = "; ".join(outcomes)

            if not parsed.get("practice_prompt"):
                parsed["practice_prompt"] = (
                    f"I'm working toward the \"{title}\" badge ({req.skill} / {req.capability} / {req.power}) in Band {req.band}.\n"
                    f"I want to practice the following topics for this badge:\n"
                    f"{topics_bullets}\n\n"
                    f"By the end I need to be able to: {outcomes_semicolon}\n\n"
                    f"Design one small, hands-on practice project that lets me demonstrate all of the topics and outcomes above together. "
                    f"Include a clear task description, any starting constraints or inputs I should assume, and what a finished/successful result looks like."
                )

            if not parsed.get("resources_prompt"):
                parsed["resources_prompt"] = (
                    f"I'm working toward the \"{title}\" badge ({req.skill} / {req.capability} / {req.power}) in Band {req.band}.\n"
                    f"I need free, current, high-quality learning resources (official docs, free courses, tutorials, videos) that help me learn:\n"
                    f"{topics_bullets}\n\n"
                    f"By the end I need to be able to: {outcomes_semicolon}\n\n"
                    f"Please suggest specific free resources for each topic above (prefer official docs, free interactive tutorials, and reputable free video/blog content over paid courses), "
                    f"and suggest one small hands-on project that lets me demonstrate all of the topics together."
                )

            parsed["practice_project"] = {
                "intro": "Want some hands-on practice? Use this prompt to generate a practice project.",
                "prompt": parsed["practice_prompt"],
                "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to generate a practice project for this badge."
            }
            parsed["learning_resources"] = {
                "intro": "Not sure where to start learning? Use this prompt to find free resources tailored to this badge.",
                "prompt": parsed["resources_prompt"],
                "footnote": "This is a prompt which should be provided to an LLM (Ex: Claude, ChatGPT, etc.) to get relevant learning resources."
            }

            return {"success": True, "badge": parsed, "mode": "gemini_live"}
    except Exception:
        # Graceful fallback to deterministic generator
        return {
            "success": True,
            "badge": generate_fallback_badge(req.band, req.power, req.capability, req.skill, req.outcome_sentence or ""),
            "mode": "fallback_on_error"
        }


@router.post("/mentor-chat")
async def mentor_chat(req: MentorChatRequest, user=Depends(get_current_user)):
    """AI Mentor chat proxy."""
    return {
        "success": True,
        "reply": f"Hello {user['name']}! Regarding '{req.badge_title}': Focus on structuring your architecture diagram and demonstrating concrete trade-offs across the 5 evaluation criteria (Business Understanding, Architecture, Technical Knowledge, Presentation, and Q&A). Let me know which criterion you'd like guidance on!"
    }
