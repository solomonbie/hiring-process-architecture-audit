# Hiring Process Architecture
### Designing evidence-led hiring systems for better decision quality

**Type** — Talent Science · Hiring Architecture · Decision Quality · Organisational Psychology
**Status** — Methodology developed in practice; interactive diagnostic tool live and in use
**Author** — Solomon Obie · [solomonobie.com](https://solomonobie.com)

---

> Hiring processes should not be measured by the number of interviews completed. They should be measured by the quality of evidence they generate for decision making.

---

## Executive summary

Most hiring processes are never designed. They accumulate. An extra interview is added after a painful hire, an assessment task grows longer, a new stakeholder joins the decision, and over time the process becomes more complex without becoming more predictive. The result is a system nobody planned, that few can explain, and that quietly leans on intuition at the moment a decision is made.

This project reframes a hiring process as an evidence-generating system, and asks a sharper question than "how many stages do we have?" — namely, *for the things we say we are hiring for, where is the evidence actually collected, and how good is that evidence?*

The output is a framework and an interactive diagnostic tool. The tool scores a hiring process across five dimensions, every one of which traces back to published personnel-selection research or is clearly labelled as a practice-based heuristic. It is live, and has been used by three companies — in fintech, consulting, and biotech — to audit and strengthen their hiring against evidence-and-competency-based principles rather than gut feel.

## Origin

The methodology did not begin as a tool. It began as repeated, hands-on hiring-architecture work at Volvo Cars, where the author designed competency-based hiring frameworks for backend software engineering roles across Java, C#, and Python. That work involved collaborating directly with engineers to design code tests and technical scripting assessments, designing the values interviews personally, and designing the scoring approach for each level of role. The frameworks and structured scorecards produced this way were adopted by hiring teams as their working basis for assessment.

What that experience made concrete is the gap this project addresses: it is comparatively easy to source candidates and run interviews, and comparatively rare to design the *system* so that each stage collects specific, comparable evidence against a defined competency. The tool is the generalisation of that hands-on practice — an attempt to make the same discipline available to teams that do not have a dedicated person to design it for them.

## The business problem

Many organisations invest heavily in sourcing, employer branding, and recruitment technology while paying far less attention to the quality of the hiring system itself. The symptoms are familiar: long hiring cycles, inconsistent interviewer feedback, candidate drop-off, conflicting recommendations after a loop, weak calibration, unclear competency definitions, and decisions that ultimately rest on impression. The challenge is frequently misdiagnosed as a talent-attraction problem when it is, in fact, a decision-architecture problem.

This is acute for startups and scaleups, which often build their first real hiring process exactly when the cost of a wrong hire is highest and the time to design carefully is shortest.

## Research question

How can an organisation design a hiring system that consistently generates high-quality evidence for decision making, while remaining efficient, fair, and tolerable for candidates?

## Theoretical framework

The framework rests on one core assumption, drawn from competency-modelling practice: values and abstract qualities cannot be measured directly — only observable behaviour can. It therefore works through six descending layers, each translating the one above into something more concrete and more measurable.

Business outcomes → Values → Competencies → Behaviours → Evidence → Decision quality

A value such as "ownership" is not assessable as stated. Translated into a competency (initiative), then into behaviours (acts before being asked; persists through a setback; takes responsibility when it could be deflected), it becomes something an interviewer can actually observe and score. The quality of a hiring decision is then a function of how much consistent evidence the process collected across those behaviours.

## Research foundations

The tool is deliberately built so that its scoring is grounded in citable sources rather than invented weights. Its principal foundations are:

- **Predictive validity of selection methods** — Schmidt & Hunter's (1998) synthesis of 85 years of research, updated by Sackett, Zhang, Berry & Lievens (2022), which corrected a long-standing overcorrection for range restriction and reordered which methods predict performance best.
- **Combination of evidence** — the body of work showing that mechanical, rubric-based combination of evidence outperforms holistic clinical judgment (Meehl; Kuncel et al., 2013).
- **Competency modelling** — Spencer & Spencer's (1993) generic competency dictionary, used to translate values into observable behaviour.
- **Skills taxonomy** — the O*NET Content Model, the U.S. Department of Labor's public occupational framework, used to give the tool a broad, role-spanning set of assessable competencies.

## What the tool does

A user describes the role and its seniority tier, the values and domain expertise they are hiring for, and their actual hiring stages — what each assesses, how it is run, whether a scorecard exists, how many interviewers are involved — and how the final decision is reached. The engine then returns five scores, each with its reasoning shown in full, a competency-coverage map, a prioritised recommendation, and a downloadable report.

### The five scores

| Score | What it measures | Basis |
|---|---|---|
| Evidence Validity | Weighted validity of the assessment methods used | Meta-analytic |
| Competency Coverage | Whether each stated value and requirement is actually assessed | Completeness check |
| Decision Process Quality | Structured rubric vs open discussion; calibration; candidate prep | Decision-science research |
| Structural Safeguard | Exposure to known risk factors for noisy/biased judgment | Risk-factor research |
| Candidate Experience | Process length and burden vs typical practice for the tier | Practice-based heuristic |

A deliberate point of design: the tool states which scores are grounded in meta-analytic research and which are informed heuristics. It does not present all five as carrying equal evidentiary weight, because they do not.

### Worked example of a finding

A process can list "Empathy" as a core value, run a take-home code test and a panel interview, and still receive a flag that empathy is never actually assessed — because a take-home has no human interaction through which to observe it, and no later stage was tagged against it. The coverage map makes this visible at a glance: a value that traces cleanly to a stage, versus one that is named on the careers page and assessed nowhere.

## Usage

The methodology was developed through the engineering-hiring work at Volvo Cars described above. The tool that generalises it is now distributed through the author's company, Avilelu, to hiring managers who use it to audit their own processes — to check that their hiring rests on evidence and a defined competency framework rather than gut feel.

To date it has been used by three companies, across fintech, consulting, and biotech, to audit and strengthen their hiring on this basis. (These organisations are not named here.) No outcome metrics are claimed for them; the tool's role in each case was diagnostic — surfacing where a process collected real evidence and where it did not.

## Limitations

This is stated plainly because intellectual honesty is part of the method.

The tool is a **diagnostic heuristic, not a validated predictive model.** Its scores have not been tested against actual quality-of-hire or retention outcomes; doing so — running the diagnosis against real hiring outcome data — is the clearest next step toward genuine validation.

Its validity coefficients predict **average job performance** and were not derived against retention, time-to-productivity, or DEI outcomes, which a complete hiring system should also weigh. A high-validity method run badly can still underperform a low-validity method run well; the figures inform design, not individual judgments.

It draws on **no proprietary frameworks.** Korn Ferry's Leadership Architect and SHL's Universal Competency Framework are licensed and are not reproduced; an organisation using one of those maps its own competency names in through free text.

One method — physical or psychomotor ability testing — is currently **excluded** because a sufficiently corroborated validity figure could not be confirmed; it is flagged as a gap to fill rather than estimated.

## What this demonstrates

The project brings together competency modelling, personnel-selection science, decision-quality research, systems design, and product thinking into a single working artefact — and does so while being explicit about the boundary between what is evidenced and what is judgment. That boundary is the point. A hiring system earns trust not by producing a confident number, but by being able to show its reasoning.

---

*Tool: [hiring-process-architecture-audit.streamlit.app](https://hiring-process-architecture-audit.streamlit.app/) · Built by Solomon Obie · [solomonobie.com](https://solomonobie.com)*
