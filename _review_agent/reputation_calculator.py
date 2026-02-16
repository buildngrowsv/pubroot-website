"""
Reputation Calculator — Pubroot

PURPOSE:
    Calculate a contributor's reputation score based on their submission history.
    Reputation drives queue priority (higher rep = faster reviews) and determines
    the review depth applied (trusted contributors skip basic checks).
    
    The reputation system is the core "trust flywheel" of the journal:
    Submit good work → build reputation → get faster reviews → submit more →
    reputation keeps climbing → eventually auto-publish tier.
    
    The inverse also works: submit spam/garbage → reputation drops → slower reviews
    → less incentive to spam → self-regulating quality without human moderation.

CALLED BY:
    review_pipeline_main.py — called after Stage 6 updates contributor stats.
    Also used by priority_score_calculator.py to fetch current reputation.

DEPENDS ON:
    - contributors.json in the repo root

FORMULA:
    reputation_score = weighted_average(
        acceptance_rate    × 0.40,   # Most important: do your submissions pass?
        normalized_avg_score × 0.30, # Quality of accepted work (score/10)
        consistency_bonus  × 0.15,   # Regular contributor bonus (log scale)
        recency_bonus      × 0.15   # Active in last 90 days?
    )
    
    Penalties (subtractive):
        - Each spam flag:              -0.10
        - Each prompt injection attempt: -0.20
        - Each DMCA strike:            -0.30
        - Inactive >180 days:          score decays by 10%/month

TIERS:
    new:        0.0           (first submission, no history)
    emerging:   0.01 – 0.39   (building track record)
    established: 0.40 – 0.69  (slight priority boost, skip format checks)
    trusted:    0.70 – 0.89   (significant priority, light review)
    authority:  0.90 – 1.00   (max priority, post-publish review)
    suspended:  -1.0          (blocked, manual review required)
"""

import json
import math
import os
from datetime import datetime, timezone, timedelta


def calculate_reputation(
    contributor_data: dict,
) -> dict:
    """
    Calculate the reputation score and tier for a single contributor.
    
    This is the ONLY public function in this file. It takes the contributor's
    stats (from contributors.json) and returns the updated reputation score
    and tier.
    
    Args:
        contributor_data: A single contributor's dict from contributors.json,
                         containing total_submissions, accepted, rejected,
                         acceptance_rate, average_score, flags, last_submission, etc.
    
    Returns:
        dict with keys:
            - 'reputation_score' (float): 0.0 to 1.0
            - 'reputation_tier' (str): 'new', 'emerging', 'established',
                                        'trusted', 'authority', or 'suspended'
    """
    
    total = contributor_data.get("total_submissions", 0)
    
    # -----------------------------------------------------------------------
    # Edge case: No submissions yet
    # -----------------------------------------------------------------------
    if total == 0:
        return {"reputation_score": 0.0, "reputation_tier": "new"}
    
    # -----------------------------------------------------------------------
    # Check for suspension first
    # -----------------------------------------------------------------------
    # Suspension happens when a contributor accumulates too many flags.
    # A suspended contributor cannot submit until manually reviewed.
    # The threshold is: 3+ spam flags, OR 2+ injection attempts, OR 1+ DMCA.
    # -----------------------------------------------------------------------
    
    flags = contributor_data.get("flags", {})
    spam = flags.get("spam_submissions", 0)
    injections = flags.get("prompt_injection_attempts", 0)
    dmca = flags.get("dmca_strikes", 0)
    
    if dmca >= 1 or injections >= 2 or spam >= 3:
        return {"reputation_score": -1.0, "reputation_tier": "suspended"}
    
    # -----------------------------------------------------------------------
    # COMPONENT 1: Acceptance Rate (weight: 0.40)
    # -----------------------------------------------------------------------
    # The most important signal. If 90% of your submissions get accepted,
    # you're consistently producing quality work. Range: 0.0 to 1.0.
    # -----------------------------------------------------------------------
    
    acceptance_rate = contributor_data.get("acceptance_rate", 0.0)
    
    # -----------------------------------------------------------------------
    # COMPONENT 2: Normalized Average Score (weight: 0.30)
    # -----------------------------------------------------------------------
    # Average review score normalized to 0-1 range (score / 10).
    # A contributor who consistently scores 8/10 gets 0.8 here.
    # -----------------------------------------------------------------------
    
    avg_score = contributor_data.get("average_score", 0.0)
    normalized_score = min(avg_score / 10.0, 1.0)
    
    # -----------------------------------------------------------------------
    # COMPONENT 3: Consistency Bonus (weight: 0.15)
    # -----------------------------------------------------------------------
    # Rewards regular contributors. Uses log scale so the first few
    # submissions matter most, then the bonus plateaus.
    # Formula: min(log2(total_submissions + 1) / 6, 1.0)
    # At 1 submission: 0.17, at 5: 0.43, at 10: 0.58, at 63+: 1.0
    # -----------------------------------------------------------------------
    
    consistency = min(math.log2(total + 1) / 6.0, 1.0)
    
    # -----------------------------------------------------------------------
    # COMPONENT 4: Recency Bonus (weight: 0.15)
    # -----------------------------------------------------------------------
    # Active contributors get a bonus. Inactive ones lose it.
    # Full bonus (1.0) if last submission was within 90 days.
    # Linear decay from 1.0 to 0.0 over days 90 to 365.
    # Zero if inactive for more than a year.
    # -----------------------------------------------------------------------
    
    last_submission_str = contributor_data.get("last_submission", "")
    recency = 0.0
    if last_submission_str:
        try:
            last_date = datetime.fromisoformat(last_submission_str)
            now = datetime.now(timezone.utc)
            days_ago = (now - last_date).days
            
            if days_ago <= 90:
                recency = 1.0
            elif days_ago <= 365:
                recency = max(0.0, 1.0 - (days_ago - 90) / 275.0)
            else:
                recency = 0.0
        except ValueError:
            recency = 0.0
    
    # -----------------------------------------------------------------------
    # WEIGHTED COMBINATION
    # -----------------------------------------------------------------------
    
    raw_score = (
        acceptance_rate * 0.40
        + normalized_score * 0.30
        + consistency * 0.15
        + recency * 0.15
    )
    
    # -----------------------------------------------------------------------
    # APPLY PENALTIES
    # -----------------------------------------------------------------------
    # Each flag type subtracts from the score. This can drive the score
    # negative, but we clamp to 0.0 minimum (unless suspended).
    # -----------------------------------------------------------------------
    
    penalty = (spam * 0.10) + (injections * 0.20) + (dmca * 0.30)
    final_score = max(0.0, min(1.0, raw_score - penalty))
    
    # -----------------------------------------------------------------------
    # INACTIVITY DECAY
    # -----------------------------------------------------------------------
    # If inactive for >180 days, the score decays by 10% per month of
    # additional inactivity. This prevents abandoned accounts from holding
    # high reputation indefinitely.
    # -----------------------------------------------------------------------
    
    if last_submission_str:
        try:
            last_date = datetime.fromisoformat(last_submission_str)
            now = datetime.now(timezone.utc)
            days_inactive = (now - last_date).days
            
            if days_inactive > 180:
                months_over = (days_inactive - 180) / 30.0
                decay_factor = max(0.0, 1.0 - (0.10 * months_over))
                final_score *= decay_factor
        except ValueError:
            pass
    
    final_score = round(final_score, 3)
    
    # -----------------------------------------------------------------------
    # DETERMINE TIER
    # -----------------------------------------------------------------------
    
    if final_score >= 0.90:
        tier = "authority"
    elif final_score >= 0.70:
        tier = "trusted"
    elif final_score >= 0.40:
        tier = "established"
    elif final_score > 0.0:
        tier = "emerging"
    else:
        tier = "new"
    
    return {
        "reputation_score": final_score,
        "reputation_tier": tier,
    }


def update_all_reputations(repo_root: str) -> dict:
    """
    Recalculate reputation for all contributors in contributors.json.
    
    This can be called after every review, or on a schedule, to ensure
    reputation scores reflect the latest submission history including
    inactivity decay.
    
    Args:
        repo_root: Path to the repo root
    
    Returns:
        dict mapping contributor handles to their updated reputation data
    """
    contributors_path = os.path.join(repo_root, "contributors.json")
    
    with open(contributors_path, "r") as f:
        data = json.load(f)
    
    contributors = data.get("contributors", {})
    updated = {}
    
    for handle, cdata in contributors.items():
        rep = calculate_reputation(cdata)
        cdata["reputation_score"] = rep["reputation_score"]
        cdata["reputation_tier"] = rep["reputation_tier"]
        updated[handle] = rep
    
    data["contributors"] = contributors
    
    with open(contributors_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return updated
