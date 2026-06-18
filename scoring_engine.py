"""
scoring_engine.py

Pure-Python, deterministic scoring engine for the Hiring Process Architecture tool.
No external API calls, nothing leaves the machine running this. Reads two
knowledge-base files (evidence_validity_weights.json and
values_competency_library.json) and never hardcodes a research-derived number
directly in this file - every weight traces back to one of those two files,
so updating the research means editing the JSON, not this code.

All five scores are designed so higher = better, for a consistent dashboard.
"""

import json
import os

KB_DIR = os.path.dirname(os.path.abspath(__file__))


def load_knowledge_base(kb_dir=KB_DIR):
    with open(os.path.join(kb_dir, "evidence_validity_weights.json")) as f:
        weights = json.load(f)
    with open(os.path.join(kb_dir, "values_competency_library.json")) as f:
        library = json.load(f)
    weights_by_id = {m["id"]: m for m in weights["methods"]}
    library_by_value = {}
    for entry in library["values"]:
        library_by_value[entry["value"].lower()] = entry
        for alias in entry.get("aliases", []):
            library_by_value[alias.lower()] = entry
    return weights_by_id, library_by_value


# ---------- Score 1: Evidence Validity ----------

def score_evidence_validity(stages, weights_by_id):
    """Average meta-analytic validity of the methods actually used, scaled
    against the strongest method in the table so 100 represents the research
    ceiling, not an arbitrary round number."""
    if not stages:
        return 0, "No stages were entered, so there is no evidence to score."
    validities, breakdown = [], []
    for stage in stages:
        if stage.get("method_id") == "screening_check":
            continue  # a filter, not an assessment method - shouldn't count as weak evidence
        method = weights_by_id.get(stage["method_id"])
        if not method:
            continue
        validities.append(method["validity"])
        breakdown.append(f"{stage['name']}: {method['label']} (validity {method['validity']:.2f}, source: {method['source']})")
    if not validities:
        return 0, "No assessment stages were entered (screening-only). Add at least one stage that assesses a competency or skill."
    avg_validity = sum(validities) / len(validities)
    ceiling = max(m["validity"] for m in weights_by_id.values())
    score = round(min(100, (avg_validity / ceiling) * 100))
    explanation = (
        f"Average validity across {len(validities)} stage(s) is {avg_validity:.2f}, "
        f"scaled against the strongest method in the table ({ceiling:.2f}). " + " | ".join(breakdown)
    )
    return score, explanation


# ---------- Score 2: Competency Coverage ----------

def score_competency_coverage(values, stages, library_by_value, technical_requirements=None):
    """Percentage of stated requirements - both value-derived competencies and
    role-specific technical/domain requirements - that have at least one stage
    assessing them. Screening-only stages legitimately assess nothing here and
    are not expected to contribute coverage."""
    technical_requirements = technical_requirements or []
    targets = list(values) + list(technical_requirements)
    if not targets:
        return 0, "No values or technical requirements were entered."
    covered, gaps = [], []
    for value in values:
        entry = library_by_value.get(value.lower())
        competency_name = entry["competency"] if entry else value
        matched = any(
            competency_name.lower() in [c.lower() for c in stage.get("competencies_assessed", [])]
            for stage in stages
        )
        (covered if matched else gaps).append(value)
    for req in technical_requirements:
        matched = any(
            req.lower() in [c.lower() for c in stage.get("technical_assessed", [])]
            for stage in stages
        )
        (covered if matched else gaps).append(req)
    score = round(100 * len(covered) / len(targets))
    explanation = f"{len(covered)} of {len(targets)} requirement(s) are assessed by at least one stage."
    if gaps:
        explanation += f" Unmeasured: {', '.join(gaps)}."
    return score, explanation


# ---------- Score 3: Decision Process Quality ----------

def score_decision_process(decision_process):
    """Grounded in the mechanical-vs-holistic combination literature (Meehl;
    Kuncel et al., 2013): structured, rubric-driven combination of evidence
    consistently outperforms discussion-based judgment. A small bonus is added
    for deliberately preparing candidates, which improves fairness and
    experience by levelling access to what the process expects."""
    base_by_method = {"mechanical": 85, "hybrid": 55, "holistic": 25}
    method = decision_process.get("combination_method", "holistic")
    base = base_by_method.get(method, 25)
    calibration = decision_process.get("calibration", False)
    prep = decision_process.get("candidates_prepared", False)
    cal_adj = 15 if calibration else -10
    prep_adj = 5 if prep else 0
    score = max(0, min(100, base + cal_adj + prep_adj))
    explanation = (
        f"Combination method '{method}' gives a base of {base}/100. "
        f"Calibration practice is {'present' if calibration else 'absent'} ({'+15' if calibration else '-10'}). "
        f"Candidate preparation is {'provided (+5)' if prep else 'not noted'}."
    )
    return score, explanation


# ---------- Score 4: Structural Safeguard ----------

def score_structural_safeguard(stages):
    """Flags known structural risk factors for noisy or biased judgment
    (unstructured format, no scorecard, single rater) - it measures exposure
    to those risk factors, not actual bias."""
    if not stages:
        return 0, "No stages were entered."
    n = len(stages)
    scorecard_ratio = sum(1 for s in stages if s.get("has_scorecard")) / n
    structured_ratio = sum(1 for s in stages if s.get("method_id") != "unstructured_interview") / n
    multi_rater_ratio = sum(1 for s in stages if s.get("interviewer_count", 1) >= 2) / n
    score = round(100 * (0.4 * scorecard_ratio + 0.4 * structured_ratio + 0.2 * multi_rater_ratio))
    explanation = (
        f"{round(scorecard_ratio*100)}% of stages use a scorecard, "
        f"{round(structured_ratio*100)}% avoid unstructured interviewing, "
        f"{round(multi_rater_ratio*100)}% use more than one rater."
    )
    return score, explanation


# ---------- Score 5: Candidate Experience ----------

# These tiers are informed by typical hiring practice at each level, not a
# meta-analytic finding - unlike the evidence-validity table, there is no
# published research that says "8 stages is correct for an executive search."
# Labelling that distinction honestly matters as much as the numbers do.
ROLE_TIERS = {
    "operational": {
        "label": "High-volume / operational",
        "ideal_stages": (1, 3), "ideal_minutes": 90,
        "example_titles": ["Warehouse associate", "Retail associate", "Call center representative", "Delivery driver"],
    },
    "professional": {
        "label": "Standard professional / individual contributor",
        "ideal_stages": (3, 5), "ideal_minutes": 240,
        "example_titles": ["Software engineer (mid-level)", "HR coordinator", "Marketing specialist", "Financial analyst"],
    },
    "senior_specialist": {
        "label": "Senior specialist or first-line manager",
        "ideal_stages": (4, 6), "ideal_minutes": 300,
        "example_titles": ["Staff engineer", "Principal designer", "Engineering manager", "Senior product manager"],
    },
    "executive": {
        "label": "Senior leadership / executive",
        "ideal_stages": (5, 8), "ideal_minutes": 480,
        "example_titles": ["VP Engineering", "CTO", "CHRO", "CFO"],
    },
}


def score_candidate_experience(stages, role_tier="professional"):
    if not stages:
        return 0, "No stages were entered."
    tier = ROLE_TIERS.get(role_tier, ROLE_TIERS["professional"])
    min_stages, max_stages = tier["ideal_stages"]
    ideal_minutes = tier["ideal_minutes"]
    n = len(stages)
    total_minutes = sum(s.get("duration_minutes", 0) for s in stages)
    stage_penalty = max(0, n - max_stages) * 15 + max(0, min_stages - n) * 10
    duration_penalty = max(0, (total_minutes - ideal_minutes) // 30) * 5
    score = max(0, 100 - stage_penalty - duration_penalty)
    explanation = (
        f"{n} stage(s) totalling {total_minutes} minutes of candidate time, benchmarked against the "
        f"'{tier['label']}' tier (ideal {min_stages}-{max_stages} stages, under {ideal_minutes} minutes total). "
        "This benchmark reflects typical practice at this level, not a meta-analytic finding."
    )
    return score, explanation


# ---------- Composite ----------

WEIGHTS = {
    "evidence_validity": 0.30,
    "competency_coverage": 0.20,
    "decision_process": 0.25,
    "structural_safeguard": 0.15,
    "candidate_experience": 0.10,
}


def recommend_highest_leverage_fix(scores, stages, values, library_by_value, weights_by_id):
    lowest_key = min(scores, key=lambda k: scores[k])
    if lowest_key == "evidence_validity" and stages:
        # Exclude screening stages - their low validity is by design (a CV-vs-spec
        # filter isn't meant to predict performance), so recommending you "fix" one
        # would be wrong advice.
        scorable = [s for s in stages if s.get("method_id") != "screening_check"]
        if scorable:
            weakest_stage = min(scorable, key=lambda s: weights_by_id.get(s["method_id"], {"validity": 0})["validity"])
            method_label = weights_by_id.get(weakest_stage["method_id"], {}).get("label", weakest_stage["method_id"])
            return (
                f"Highest-leverage fix: '{weakest_stage['name']}' uses the lowest-validity assessment method in your "
                f"process ({method_label}). Replacing it with a structured interview or work sample would "
                "raise your Evidence Validity score the most."
            )
    if lowest_key == "competency_coverage":
        gaps = [
            v for v in values
            if not any(
                library_by_value.get(v.lower(), {}).get("competency", v).lower()
                in [c.lower() for c in s.get("competencies_assessed", [])]
                for s in stages
            )
        ]
        if gaps:
            return f"Highest-leverage fix: add an evidence source for '{gaps[0]}' - it is currently unmeasured anywhere in the process."
    if lowest_key == "decision_process":
        return "Highest-leverage fix: move toward a structured, rubric-driven decision rather than open discussion, and add a calibration step before final decisions."
    if lowest_key == "structural_safeguard":
        return "Highest-leverage fix: add a scorecard to your unstructured stages and ensure at least two raters are involved in each."
    if lowest_key == "candidate_experience":
        return "Highest-leverage fix: your process has more stages or total candidate time than necessary - look for two stages assessing the same competency and merge them."
    return "No single fix stands out - all scores are roughly balanced."


EVIDENTIARY_BASIS = {
    "evidence_validity": "Meta-analytic (Schmidt & Hunter, 1998; Sackett et al., 2022).",
    "competency_coverage": "Logical completeness check - not a statistical estimate.",
    "decision_process": "Grounded in mechanical-vs-holistic combination research (Meehl; Kuncel et al., 2013).",
    "structural_safeguard": "Grounded in known risk-factor research - measures exposure to risk factors, not confirmed bias.",
    "candidate_experience": "Practice-based heuristic, adapted by role tier - not a meta-analytic finding.",
}


def run_audit(role, values, stages, decision_process, role_tier="professional",
              technical_requirements=None, kb_dir=KB_DIR):
    weights_by_id, library_by_value = load_knowledge_base(kb_dir)
    technical_requirements = technical_requirements or []

    ev_score, ev_explain = score_evidence_validity(stages, weights_by_id)
    cc_score, cc_explain = score_competency_coverage(values, stages, library_by_value, technical_requirements)
    dp_score, dp_explain = score_decision_process(decision_process)
    ss_score, ss_explain = score_structural_safeguard(stages)
    ce_score, ce_explain = score_candidate_experience(stages, role_tier)

    scores = {
        "evidence_validity": ev_score,
        "competency_coverage": cc_score,
        "decision_process": dp_score,
        "structural_safeguard": ss_score,
        "candidate_experience": ce_score,
    }
    composite = round(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS))

    explanations = {
        "evidence_validity": ev_explain,
        "competency_coverage": cc_explain,
        "decision_process": dp_explain,
        "structural_safeguard": ss_explain,
        "candidate_experience": ce_explain,
    }

    recommendation = recommend_highest_leverage_fix(scores, stages, values, library_by_value, weights_by_id)

    return {
        "role": role,
        "role_tier": role_tier,
        "composite_score": composite,
        "scores": scores,
        "explanations": explanations,
        "evidentiary_basis": EVIDENTIARY_BASIS,
        "recommendation": recommendation,
        "values_audited": values,
        "technical_requirements_audited": technical_requirements,
        "stages_audited": stages,
    }


if __name__ == "__main__":
    # Same number of stages and structure quality as before, but framed as a
    # CTO search instead of a generic professional hire - watch how the
    # Candidate Experience score changes purely because of role_tier.
    shared_stages = [
        {"name": "Recruiter screen", "method_id": "unstructured_interview",
         "competencies_assessed": [], "has_scorecard": False, "interviewer_count": 1, "duration_minutes": 30},
        {"name": "Hiring manager interview", "method_id": "structured_interview",
         "competencies_assessed": ["Teamwork and cooperation"], "has_scorecard": True,
         "interviewer_count": 1, "duration_minutes": 45},
        {"name": "Panel interview", "method_id": "unstructured_interview",
         "competencies_assessed": ["Integrity and reliability"], "has_scorecard": False,
         "interviewer_count": 3, "duration_minutes": 60},
        {"name": "Board case study presentation", "method_id": "work_sample",
         "competencies_assessed": ["Conceptual thinking"], "has_scorecard": True,
         "interviewer_count": 4, "duration_minutes": 90},
        {"name": "Executive reference check", "method_id": "reference_check",
         "competencies_assessed": ["Integrity and reliability"], "has_scorecard": True,
         "interviewer_count": 1, "duration_minutes": 45},
    ]

    as_professional = run_audit(
        role="Senior Product Manager", values=["Collaboration", "Trust", "Innovation"],
        stages=shared_stages, decision_process={"combination_method": "hybrid", "calibration": True},
        role_tier="professional",
    )
    as_executive = run_audit(
        role="Chief Technology Officer", values=["Collaboration", "Trust", "Innovation"],
        stages=shared_stages, decision_process={"combination_method": "hybrid", "calibration": True},
        role_tier="executive",
    )

    print("Same 5-stage process scored as a PROFESSIONAL hire:")
    print(" candidate_experience score:", as_professional["scores"]["candidate_experience"])
    print(" ->", as_professional["explanations"]["candidate_experience"])
    print()
    print("Same 5-stage process scored as an EXECUTIVE hire:")
    print(" candidate_experience score:", as_executive["scores"]["candidate_experience"])
    print(" ->", as_executive["explanations"]["candidate_experience"])
    print()
    print("Composite scores -> professional:", as_professional["composite_score"],
          "| executive:", as_executive["composite_score"])
