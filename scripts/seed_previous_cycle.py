"""
Populates the Previous Cycle (cycle_0: Jan–Jun 2026) with complete synthetic Learning data
and dual-role performance appraisals into `data/starapp.db` without disturbing active cycle_1.
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from starapp.storage import store
from starapp.previous_cycle_seed import ensure_previous_cycle_in_store, PREV_CYCLE_ID


def main():
    store.load_from_json(None)
    created = ensure_previous_cycle_in_store(store, finalize_appraisals=True)
    c0_badges = store.get_all_badges(cycle_id=PREV_CYCLE_ID)
    c0_subs = store.get_all_submissions(cycle_id=PREV_CYCLE_ID)
    c0_asms = store.get_all_assessments(cycle_id=PREV_CYCLE_ID)
    c0_apps = store.get_cycle_appraisals(PREV_CYCLE_ID)
    print(f"[seed_previous_cycle] {'Seeded' if created else 'Already present'}: {PREV_CYCLE_ID}")
    print(f"  Badges: {len(c0_badges)} | Submissions: {len(c0_subs)} | Assessments: {len(c0_asms)} | Appraisals: {len(c0_apps)}")
    print(f"  Active cycle remains: {store.get_active_cycle_id()}")


if __name__ == "__main__":
    main()
