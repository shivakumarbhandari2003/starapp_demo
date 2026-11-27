"""Shared test helper for the project-request workflow.

A cosmonaut can only submit deliverables for a project their mapped reviewer has SENT. Tests that exercise
submission / assessment use `give_project` to put that project in place, exactly as the reviewer's
"Send Project to Mapped Cosmonauts" action would.
"""
from starapp.models import ReviewerProjectPrompt


def give_project(store, badge_id, cosmonaut_id, reviewer_id=None,
                 title="SmartFit: The Member Intelligence Challenge",
                 content="Case Study\nSmartFit is a digital fitness platform.\n\nYour Challenge\nRecommend how SmartFit should organise its information."):
    """Send a released project for (badge, cosmonaut) from the cosmonaut's mapped reviewer (or `reviewer_id`)."""
    rev = reviewer_id or store.get_mapped_reviewer_id(badge_id, cosmonaut_id) or "guardian_1"
    prompt = ReviewerProjectPrompt(
        id=f"proj_{badge_id}_{rev}_{cosmonaut_id}",
        badge_id=badge_id,
        reviewer_id=rev,
        cosmonaut_ids=[cosmonaut_id],
        title=title,
        description=content,
        status="released",
    )
    store.save_reviewer_project_prompt(prompt)
    return prompt
