# Hiring Process Architecture Audit

An evidence-led diagnostic that scores a hiring process against published personnel-selection research, rather than against a checklist of opinions.

Most hiring processes grow by accretion — a stage added after a bad hire, an extra interviewer added for comfort — until no one can say what the process actually measures or how well. This tool treats a hiring process as an evidence-generating system and asks a sharper question: *for the things you say you're hiring for, where is the evidence actually being collected, and how good is it?*

## What it does

You describe your role, the values and domain expertise you're hiring for, and your hiring stages — what each one assesses, how it's run, and how the final decision is made. The tool returns five scores, each with its reasoning shown, plus a competency-coverage map and a downloadable report.

The five scores:

- **Evidence Validity** — a weighted average of your stages' assessment methods, weighted by their meta-analytic predictive validity for job performance.
- **Competency Coverage** — whether each value and domain requirement you named is actually assessed somewhere in the process.
- **Decision Process Quality** — whether evidence is combined through a structured rubric or through open discussion, and whether interviewers are calibrated.
- **Structural Safeguard** — exposure to known structural risk factors for noisy or biased judgment (no scorecard, unstructured format, single rater).
- **Candidate Experience** — process length and burden, benchmarked against typical practice for the role's seniority tier.

## How it stays honest

Every weight the engine uses lives in an inspectable knowledge-base file, not buried in code, so the reasoning is auditable and the research can be updated without touching the application.

- `evidence_validity_weights.json` — method validity coefficients, each tagged with its source.
- `values_competency_library.json` — translates abstract values into observable competencies and behavioral indicators.
- `competency_taxonomy.json` — a broad, role-spanning competency taxonomy a stage can assess from.

The tool distinguishes between scores grounded in meta-analytic research and those that are informed practice-based heuristics, and says which is which.

## Sources

- Schmidt, F. L., & Hunter, J. E. (1998). The validity and utility of selection methods in personnel psychology. *Psychological Bulletin*, 124(2).
- Sackett, P. R., Zhang, C., Berry, C. M., & Lievens, F. (2022). Revisiting meta-analytic estimates of validity in personnel selection. *Journal of Applied Psychology*, 107(11).
- Spencer, L. M., & Spencer, S. M. (1993). *Competence at Work: Models for Superior Performance.* Wiley.
- O*NET Content Model, U.S. Department of Labor (public domain).
- Mechanical-vs-holistic combination research (Meehl; Kuncel et al., 2013).

## Limitations

This is a diagnostic heuristic, not a validated predictive model. Its scores have not been tested against actual quality-of-hire or retention outcomes — doing so is the natural next step. It draws on no proprietary frameworks (e.g. Korn Ferry, SHL); organizations using those can map their own competency names in via free text. Validity coefficients predict average job performance and were not derived against retention or DEI outcomes, which a complete hiring system should also weigh.

## Running locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Built by

Solomon Obie — [solomonobie.com](https://solomonobie.com)
