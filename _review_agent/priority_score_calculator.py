"""
Priority Score Calculator — Pubroot

PURPOSE:
    Calculate the queue priority for a new submission and assign a GitHub label
    that controls when the submission gets reviewed. Priority is based on three
    factors: contributor reputation (earned), payment tier (bought), and topic
    demand (how open the slot is).
    
    This creates two acceleration lanes:
    - Reputation-based: veterans get fast-tracked because their work is more
      likely to pass, meaning less wasted compute on rejections
    - Payment-based: new contributors can pay to jump the queue, generating
      revenue to cover API costs

CALLED BY:
    review_pipeline_main.py — called early in the pipeline (before the full
    review runs) to assign the priority label. The cron-triggered review
    workflow then processes submissions in priority order.

DEPENDS ON:
    - contributors.json for contributor reputation lookup
    - journals.json for topic demand/slot info

FORMULA:
    priority = (3.0 × reputation) + (2.0 × payment_tier) + (1.5 × topic_demand) + 1.0
    
    Where:
        reputation:   0.0 to 1.0 (from contributors.json)
        payment_tier: 0 (free), 1 (paid $5), 2 (premium)
        topic_demand: 0.0 to 1.0 (based on journals.json slot availability)
        base_score:   1.0 (everyone gets at least this)

LABELS:
    priority:critical  (score >= 5.0) — reviewed within minutes
    priority:high      (score 3.0-4.9) — reviewed within 1 hour
    priority:normal    (score 1.5-2.9) — reviewed within 6 hours
    priority:low       (score < 1.5)   — reviewed within 24 hours
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


def calculate_priority(
    author: str,
    category: str,
    payment_code: Optional[str],
    repo_root: str
) -> dict:
    """
    Calculate the priority score and label for a submission.
    
    This is the ONLY public function in this file. It looks up the contributor's
    reputation, checks for payment, evaluates topic demand, and returns the
    priority score with the corresponding GitHub label.
    
    Args:
        author: GitHub handle of the submitter
        category: Category slug from the submission
        payment_code: Payment confirmation code (or None for free tier)
        repo_root: Path to the repo root
    
    Returns:
        dict with keys:
            - 'priority_score' (float): The calculated priority value
            - 'priority_label' (str): One of 'priority:critical', 'priority:high',
                                       'priority:normal', 'priority:low'
            - 'reputation_score' (float): The contributor's current reputation
            - 'reputation_tier' (str): The contributor's tier
            - 'payment_tier' (int): 0=free, 1=paid, 2=premium
            - 'topic_demand' (float): 0.0 to 1.0
    """
    
    # -----------------------------------------------------------------------
    # STEP 1: Look up contributor reputation
    # -----------------------------------------------------------------------
    
    reputation_score = 0.0
    reputation_tier = "new"
    
    contributors_path = os.path.join(repo_root, "contributors.json")
    try:
        with open(contributors_path, "r") as f:
            data = json.load(f)
        contributor = data.get("contributors", {}).get(author, {})
        reputation_score = contributor.get("reputation_score", 0.0)
        reputation_tier = contributor.get("reputation_tier", "new")
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    # -----------------------------------------------------------------------
    # STEP 2: Determine payment tier
    # -----------------------------------------------------------------------
    # Payment codes are validated against Stripe in a later phase.
    # For now, we check if a code was provided at all. The actual Stripe
    # validation happens in the Cloudflare Worker webhook handler (Priority 8).
    # For the MVP, presence of any payment code = paid tier.
    # -----------------------------------------------------------------------
    
    payment_tier = 0
    if payment_code and payment_code.strip():
        payment_tier = 1  # Basic paid acceleration
        # Future: check for premium codes (payment_tier = 2)
    
    # -----------------------------------------------------------------------
    # STEP 3: Calculate topic demand
    # -----------------------------------------------------------------------
    # Topic demand measures how "open" a category's slot is. If a category
    # with a refresh rate just had its slot open (or is always open), demand
    # is high (1.0). If the slot was just filled, demand is low (0.0).
    # Categories with refresh_rate_days=0 are always at demand 1.0.
    # -----------------------------------------------------------------------
    
    topic_demand = _calculate_topic_demand(repo_root, category)
    
    # -----------------------------------------------------------------------
    # STEP 4: Calculate priority score
    # -----------------------------------------------------------------------
    
    REPUTATION_WEIGHT = 3.0
    PAYMENT_WEIGHT = 2.0
    TOPIC_DEMAND_WEIGHT = 1.5
    BASE_SCORE = 1.0
    
    priority_score = (
        REPUTATION_WEIGHT * reputation_score
        + PAYMENT_WEIGHT * payment_tier
        + TOPIC_DEMAND_WEIGHT * topic_demand
        + BASE_SCORE
    )
    
    priority_score = round(priority_score, 2)
    
    # -----------------------------------------------------------------------
    # STEP 5: Map score to label
    # -----------------------------------------------------------------------
    
    if priority_score >= 5.0:
        priority_label = "priority:critical"
    elif priority_score >= 3.0:
        priority_label = "priority:high"
    elif priority_score >= 1.5:
        priority_label = "priority:normal"
    else:
        priority_label = "priority:low"
    
    return {
        "priority_score": priority_score,
        "priority_label": priority_label,
        "reputation_score": reputation_score,
        "reputation_tier": reputation_tier,
        "payment_tier": payment_tier,
        "topic_demand": topic_demand,
    }


# ---------------------------------------------------------------------------
# PRIVATE HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def _calculate_topic_demand(repo_root: str, category: str) -> float:
    """
    Calculate topic demand based on slot availability in journals.json.
    
    Categories with refresh_rate_days=0 (always open) return 1.0.
    Categories with refresh rates return a value based on how close the
    slot opening date is:
    - Slot just opened: 1.0 (high demand, competitive)
    - Slot opens in < 7 days: 0.5 (moderate demand)
    - Slot not available: 0.0 (no demand, slot blocked)
    """
    journals_path = os.path.join(repo_root, "journals.json")
    
    try:
        with open(journals_path, "r") as f:
            journals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 1.0  # Default to open if we can't read journals
    
    journal_config = journals.get("journals", {}).get(category, {})
    refresh_days = journal_config.get("refresh_rate_days", 0)
    
    if refresh_days == 0:
        return 1.0  # Always open category
    
    # Check when the last paper was published in this category
    index_path = os.path.join(repo_root, "agent-index.json")
    try:
        with open(index_path, "r") as f:
            index = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 1.0  # No papers yet, slot is open
    
    papers = index.get("papers", [])
    now = datetime.now(timezone.utc)
    
    latest_date = None
    for paper in papers:
        if paper.get("category") == category:
            pub_str = paper.get("published_date")
            if pub_str:
                try:
                    pub_date = datetime.fromisoformat(pub_str)
                    if latest_date is None or pub_date > latest_date:
                        latest_date = pub_date
                except ValueError:
                    continue
    
    if latest_date is None:
        return 1.0  # No papers in this category yet
    
    slot_opens = latest_date + timedelta(days=refresh_days)
    
    if now >= slot_opens:
        return 1.0  # Slot is open
    
    days_until = (slot_opens - now).days
    if days_until <= 7:
        return 0.5  # Opening soon
    
    return 0.0  # Slot blocked
