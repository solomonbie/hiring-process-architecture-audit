"""
app.py

Streamlit front-end for the Hiring Process Architecture Audit.
Reads the same two knowledge-base files the scoring engine uses, so the
dropdown options on screen are always identical to what the engine scores
against - there is no separate, hand-maintained list of methods or values
hiding in the UI layer.
"""

import json
import os

import streamlit as st

from scoring_engine import ROLE_TIERS, STAGE_PURPOSES, generate_architecture, run_audit
from scoring_engine import load_knowledge_base
import onet_client

KB_DIR = os.path.dirname(os.path.abspath(__file__))


@st.cache_data
def load_raw_kb():
    with open(os.path.join(KB_DIR, "evidence_validity_weights.json")) as f:
        weights = json.load(f)
    with open(os.path.join(KB_DIR, "values_competency_library.json")) as f:
        library = json.load(f)
    with open(os.path.join(KB_DIR, "competency_taxonomy.json")) as f:
        taxonomy = json.load(f)
    return weights, library, taxonomy


weights_json, library_json, taxonomy_json = load_raw_kb()
METHOD_OPTIONS = {m["id"]: m["label"] for m in weights_json["methods"]}
VALUE_OPTIONS = [v["value"] for v in library_json["values"]]
VALUE_TO_COMPETENCY = {v["value"]: v["competency"] for v in library_json["values"]}
VALUE_TO_INDICATORS = {v["value"]: v.get("behavioral_indicators", []) for v in library_json["values"]}
VALUE_TO_DEFINITION = {v["value"]: v.get("definition", "") for v in library_json["values"]}
# Flat, de-duplicated list of every competency in the taxonomy, kept in category order.
TAXONOMY_COMPETENCIES = []
for cat in taxonomy_json["categories"]:
    for comp in cat["competencies"]:
        if comp not in TAXONOMY_COMPETENCIES:
            TAXONOMY_COMPETENCIES.append(comp)

st.set_page_config(page_title="Hiring Process Architecture Audit", layout="centered")
st.title("Hiring Process Architecture Audit")
st.caption(
    "An evidence-weighted diagnostic for your hiring process, grounded in personnel-selection "
    "research - every score traces back to a cited source, not a checklist point system."
)

if "stages" not in st.session_state:
    st.session_state.stages = []

# ---------- 1. Role ----------
st.header("1. Role")
role_name = st.text_input("Role title", placeholder="e.g. Staff Engineer")
role_tier = st.selectbox("Role tier", options=list(ROLE_TIERS.keys()), format_func=lambda k: ROLE_TIERS[k]["label"])
st.caption("Examples: " + ", ".join(ROLE_TIERS[role_tier]["example_titles"]))

# ---------- 2. Values ----------
st.header("2. Values you're hiring for")
selected_values = st.multiselect("Pick the values this role should embody", options=VALUE_OPTIONS)
custom_values_raw = st.text_input("Add custom values not listed above (optional, comma-separated)")
custom_values = [v.strip() for v in custom_values_raw.split(",") if v.strip()]
if custom_values:
    selected_values = selected_values + custom_values
    st.caption(
        f"{len(custom_values)} custom value(s) added - {', '.join(custom_values)} - "
        "will be treated as their own competencies, since they aren't in the library yet."
    )

if selected_values:
    with st.expander("See how each value breaks down into measurable traits", expanded=True):
        st.caption(
            "You can't measure a value like 'Ownership' directly - only the observable behaviours that "
            "demonstrate it. Each value below is broken down into the competency it maps to and the specific "
            "traits an interviewer can actually watch for and score."
        )
        for v in selected_values:
            comp = VALUE_TO_COMPETENCY.get(v, v)
            indicators = VALUE_TO_INDICATORS.get(v, [])
            definition = VALUE_TO_DEFINITION.get(v, "")
            if indicators:
                st.markdown(f"**{v}** → *{comp}*")
                if definition:
                    st.caption(definition)
                for ind in indicators:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;• {ind}", unsafe_allow_html=True)
            else:
                st.markdown(f"**{v}** *(custom)* — not in the library yet, so define the traits you'd watch for yourself.")
            st.markdown("")

# ---------- 2b. Technical / domain requirements ----------
st.header("3. Domain expertise")
DOMAIN_EXAMPLES = {
    "operational": "e.g. Equipment operation, Safety procedures, Logistics coordination",
    "professional": "e.g. Python proficiency, Financial modelling, Campaign analytics",
    "senior_specialist": "e.g. System design, Team leadership, Portfolio strategy",
    "executive": "e.g. Org design, P&L ownership, Board governance",
}
st.caption(
    "The role-specific knowledge or skill a practical assessment, case study, code test or work sample "
    "is built to measure - distinct from values. This is operational know-how in hands-on roles, technical "
    "depth in specialist roles, and strategic/functional expertise in leadership roles. Leave blank if it "
    "doesn't apply."
)
technical_raw = st.text_input(
    "List the domain expertise this role requires, comma-separated",
    placeholder=DOMAIN_EXAMPLES.get(role_tier, DOMAIN_EXAMPLES["professional"]),
)
technical_requirements = [t.strip() for t in technical_raw.split(",") if t.strip()]

# ---------- 3. Stages ----------
st.header("4. Map your hiring process")

if selected_values:
    translation_lines = []
    for v in selected_values:
        comp = VALUE_TO_COMPETENCY.get(v, v)
        if comp == v:
            translation_lines.append(f"**{v}** (custom \u2014 assessed as itself)")
        else:
            translation_lines.append(f"**{v}** \u2192 *{comp}*")
    st.info(
        "Your values translate to these measurable competencies. The stage dropdowns below use the "
        "competency names, since those are what an interviewer can actually observe:\n\n"
        + "  \u00b7  ".join(translation_lines)
    )

if st.button("+ Add a stage"):
    st.session_state.stages.append(
        {"name": "", "method_id": "structured_interview", "competencies_assessed": [],
         "technical_assessed": [], "purposes": [], "has_scorecard": False, "interviewer_count": 1, "duration_minutes": 30}
    )

competency_choices = sorted({VALUE_TO_COMPETENCY.get(v, v) for v in selected_values}) if selected_values else []

# Competencies that require live human interaction to assess credibly. Tagging
# these on a no-interaction method (take-home, code test, knowledge test) is
# weak evidence - we flag it gently rather than blocking it.
INTERACTION_COMPETENCIES = {
    "interpersonal understanding", "teamwork and cooperation", "customer service orientation",
    "directiveness and assertiveness", "valuing different perspectives", "integrity and reliability",
    "social perceptiveness", "persuasion", "negotiation", "coordination", "service orientation",
}
NO_INTERACTION_METHODS = {"take_home_assignment", "work_sample", "job_knowledge_test",
                          "cognitive_ability_test", "personality_test", "biodata", "integrity_test"}

# The picker offers, in priority order: the competencies your chosen values map to,
# then the rest of the broad taxonomy, then your domain-expertise items. Free text
# below catches anything not named here.
value_competencies = competency_choices
rest_of_taxonomy = [c for c in TAXONOMY_COMPETENCIES if c not in value_competencies]

remove_index = None
for i, stage in enumerate(st.session_state.stages):
    with st.expander(f"Stage {i + 1}: {stage['name'] or 'Untitled'}", expanded=True):
        stage["name"] = st.text_input("Stage name", value=stage["name"], key=f"name_{i}")
        method_keys = list(METHOD_OPTIONS.keys())
        stage["method_id"] = st.selectbox(
            "Evaluation method", options=method_keys, format_func=lambda k: METHOD_OPTIONS[k],
            index=method_keys.index(stage["method_id"]), key=f"method_{i}",
        )

        purpose_keys = list(STAGE_PURPOSES.keys())
        stage["purposes"] = st.multiselect(
            "What is the purpose of this stage?",
            options=purpose_keys, format_func=lambda k: STAGE_PURPOSES[k],
            default=[p for p in stage.get("purposes", []) if p in purpose_keys],
            key=f"purpose_{i}",
            help="What this stage exists to do. Two stages with the same purpose may be redundant.",
        )

        if stage["method_id"] == "screening_check":
            st.caption("Screening confirms eligibility (CV vs spec, salary, location). It doesn't assess competencies, so there's nothing to tag here.")
            stage["competencies_assessed"] = []
            stage["technical_assessed"] = []
        else:
            comp_options = (
                [("comp", c, "Your values") for c in value_competencies]
                + [("comp", c, "Taxonomy") for c in rest_of_taxonomy]
                + [("tech", t, "Domain") for t in technical_requirements]
            )
            prev = set(stage.get("competencies_assessed", [])) | set(stage.get("technical_assessed", []))
            chosen = st.multiselect(
                "What does this stage actually assess?",
                options=comp_options,
                default=[o for o in comp_options if o[1] in prev],
                format_func=lambda o: f"{o[1]}  ·  {o[2]}" if o[0] == "comp" else f"{o[1]}  ·  Domain",
                key=f"assess_{i}",
            )
            free_text_raw = st.text_input(
                "Assessing something not in the list? Add it (comma-separated)",
                value=", ".join(stage.get("free_text_assessed", [])),
                key=f"free_{i}",
            )
            free_text = [f.strip() for f in free_text_raw.split(",") if f.strip()]
            stage["free_text_assessed"] = free_text
            stage["competencies_assessed"] = [val for kind, val, _ in chosen if kind == "comp"] + free_text
            stage["technical_assessed"] = [val for kind, val, _ in chosen if kind == "tech"]

            if stage["method_id"] in NO_INTERACTION_METHODS:
                flagged = [c for c in stage["competencies_assessed"] if c.lower() in INTERACTION_COMPETENCIES]
                if flagged:
                    st.caption(
                        f"⚠️ {METHOD_OPTIONS[stage['method_id']]} involves no live interaction, so it's weak evidence for: "
                        f"{', '.join(flagged)}. These are usually better assessed in a structured interview."
                    )

        c1, c2, c3 = st.columns(3)
        with c1:
            stage["has_scorecard"] = st.checkbox("Uses a scorecard", value=stage["has_scorecard"], key=f"sc_{i}")
        with c2:
            stage["interviewer_count"] = st.number_input(
                "Interviewers", min_value=1, max_value=10, value=stage["interviewer_count"], key=f"ic_{i}"
            )
        with c3:
            stage["duration_minutes"] = st.number_input(
                "Duration (min)", min_value=5, max_value=480, value=stage["duration_minutes"], step=5, key=f"dur_{i}"
            )
        if st.button("Remove this stage", key=f"rm_{i}"):
            remove_index = i

if remove_index is not None:
    st.session_state.stages.pop(remove_index)
    st.rerun()

# ---------- 4. Decision process ----------
st.header("5. How is the final decision made?")
combination_method = st.radio(
    "Combination method",
    options=["mechanical", "hybrid", "holistic"],
    format_func=lambda m: {
        "mechanical": "Structured rubric / scorecard combination",
        "hybrid": "Mix of rubric and discussion",
        "holistic": "Open discussion / consensus",
    }[m],
)
calibration = st.checkbox("Interviewers are calibrated (trained together on what 'good' looks like)")
candidates_prepared = st.checkbox("Candidates are deliberately prepared (sent materials, briefed on format)")

# ---------- Run ----------
st.divider()
run_clicked = st.button("Run the audit", type="primary", use_container_width=True)

if run_clicked:
    if not st.session_state.stages:
        st.error("Add at least one stage before running the audit.")
    elif not selected_values and not technical_requirements:
        st.error("Add at least one value or technical requirement before running the audit.")
    else:
        st.session_state.last_result = run_audit(
            role=role_name or "Unnamed role",
            values=selected_values,
            stages=st.session_state.stages,
            decision_process={
                "combination_method": combination_method,
                "calibration": calibration,
                "candidates_prepared": candidates_prepared,
            },
            role_tier=role_tier,
            technical_requirements=technical_requirements,
        )

# The generator only becomes available once a process has been audited. Clicking
# "Generate" reveals a panel asking for the optional O*NET key with a privacy
# note; a second "Generate now" button actually runs it.
if "last_result" in st.session_state:
    st.markdown("##### Next step")
    st.caption("Now that your process is audited, generate a research-grounded starting architecture to compare against.")
    if st.button("Generate recommended architecture", use_container_width=True):
        st.session_state.show_gen_panel = True

onet_key = ""
gen_now = False
if st.session_state.get("show_gen_panel"):
    with st.container(border=True):
        st.markdown("**Optional: enrich with U.S. Department of Labor (O*NET) role data**")
        st.caption(
            "Paste a free O*NET API key to pull the skills O*NET rates as most important for this role. "
            "Your key is used only for this one generation and is never stored or saved. "
            "Leave it blank to generate from the built-in knowledge base instead."
        )
        onet_key = st.text_input("O*NET API key (optional)", type="password", key="onet_key_input")
        gen_now = st.button("Generate now", type="primary", use_container_width=True)

if gen_now:
    if not selected_values and not technical_requirements:
        st.error("Add at least one value or domain requirement before generating an architecture.")
    else:
        _, lib_for_gen = load_knowledge_base(KB_DIR)
        weights_for_gen = {m["id"]: m for m in weights_json["methods"]}
        onet_skills = []
        if onet_key and role_name:
            with st.spinner("Fetching role data from O*NET…"):
                enriched = onet_client.enrich_role(role_name, onet_key)
                onet_skills = enriched.get("skills", [])
        st.session_state.generated_arch = generate_architecture(
            role=role_name or "Unnamed role",
            values=selected_values,
            technical_requirements=technical_requirements,
            role_tier=role_tier,
            library_by_value=lib_for_gen,
            weights_by_id=weights_for_gen,
            onet_skills=onet_skills,
        )

def score_color(score):
    if score >= 70:
        return "#1D9E75"
    if score >= 45:
        return "#BA7517"
    return "#E24B4A"


def render_score_bar(label, score, explanation, basis):
    color = score_color(score)
    st.markdown(
        f"""
        <div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:baseline;">
            <span style="font-weight:500;font-size:15px;">{label}</span>
            <span style="font-weight:500;font-size:15px;color:{color};">{score}/100</span>
          </div>
          <div style="background:#eee;border-radius:6px;height:8px;margin:6px 0;">
            <div style="background:{color};width:{score}%;height:8px;border-radius:6px;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Why this score"):
        st.caption(explanation)
        st.markdown(f"*Evidentiary basis: {basis}*")


SCORE_LABELS = {
    "evidence_validity": "Evidence validity",
    "competency_coverage": "Competency coverage",
    "decision_process": "Decision process quality",
    "structural_safeguard": "Structural safeguard",
    "candidate_experience": "Candidate experience",
}

def build_report_html(result, library_by_value):
    rows = ""
    for key in SCORE_LABELS:
        rows += (
            f"<tr><td>{SCORE_LABELS[key]}</td>"
            f"<td style='text-align:right;font-weight:600;color:{score_color(result['scores'][key])}'>{result['scores'][key]}/100</td></tr>"
            f"<tr><td colspan='2' style='font-size:12px;color:#555;padding-bottom:10px;'>{result['explanations'][key]}<br><em>Basis: {result['evidentiary_basis'][key]}</em></td></tr>"
        )
    coverage = ""
    for value in result["values_audited"]:
        entry = library_by_value.get(value.lower())
        competency = entry["competency"] if entry else value
        assessed_in = [
            s["name"] for s in result["stages_audited"]
            if competency.lower() in [c.lower() for c in s.get("competencies_assessed", [])]
        ]
        if assessed_in:
            coverage += f"<li><strong>{value}</strong> &rarr; <em>{competency}</em> &rarr; assessed in: {', '.join(assessed_in)}</li>"
        else:
            coverage += f"<li style='color:#A32D2D;'><strong>{value}</strong> &rarr; <em>{competency}</em> &rarr; <strong>not assessed anywhere</strong></li>"
    for req in result.get("technical_requirements_audited", []):
        assessed_in = [
            s["name"] for s in result["stages_audited"]
            if req.lower() in [t.lower() for t in s.get("technical_assessed", [])]
        ]
        if assessed_in:
            coverage += f"<li><strong>{req}</strong> <em>(domain)</em> &rarr; assessed in: {', '.join(assessed_in)}</li>"
        else:
            coverage += f"<li style='color:#A32D2D;'><strong>{req}</strong> <em>(domain)</em> &rarr; <strong>not assessed anywhere</strong></li>"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Hiring Process Architecture Audit - {result['role']}</title>
<style>body{{font-family:-apple-system,Arial,sans-serif;max-width:720px;margin:40px auto;padding:0 20px;color:#1a1a1a;line-height:1.6;}}
h1{{font-size:22px;}} h2{{font-size:17px;margin-top:28px;}} table{{width:100%;border-collapse:collapse;}}
td{{padding:4px 0;border-bottom:0.5px solid #eee;}} .big{{font-size:48px;font-weight:600;color:{score_color(result['composite_score'])};}}
.fix{{background:#FAEEDA;padding:12px 16px;border-radius:8px;}} footer{{margin-top:40px;font-size:12px;color:#888;border-top:0.5px solid #eee;padding-top:12px;}}</style></head>
<body>
<h1>Hiring process architecture audit</h1>
<p style="color:#555;">Role: <strong>{result['role']}</strong> &middot; Tier: {ROLE_TIERS[result['role_tier']]['label']}</p>
<p class="big">{result['composite_score']}<span style="font-size:18px;color:#888;"> / 100 composite</span></p>
<p style="margin-top:-8px;"><strong>{result['benchmark_zone']['label']}</strong> ({result['benchmark_zone']['range']}) &middot; Architecture maturity: <strong>Level {result['maturity']['level']} of 5 — {result['maturity']['label']}</strong><br><span style="color:#666;font-size:13px;">{result['maturity']['blurb']}</span></p>
<h2>Score breakdown</h2>
<table>{rows}</table>
<h2>Evidence density</h2>
<p><strong>{result['evidence_density']['density']}</strong> ({result['evidence_density']['band']}) — {result['evidence_density']['explanation']}</p>
<h2>Decision confidence</h2>
<p><strong>{result['decision_confidence']['confidence']}%</strong> — {result['decision_confidence']['explanation']}</p>
<h2>Highest-leverage fix</h2>
<p class="fix">{result['recommendation']}</p>
<h2>Competency coverage map</h2>
<ul>{coverage}</ul>
<footer>Generated by the Hiring Process Architecture Audit. Scores derive from published personnel-selection research (Schmidt &amp; Hunter, 1998; Sackett et al., 2022) and the Spencer &amp; Spencer (1993) competency framework. This is a diagnostic heuristic, not a validated predictive model. Built by Solomon Obie &middot; <a href="https://solomonobie.com">solomonobie.com</a>.</footer>
</body></html>"""


if "last_result" in st.session_state:
    result = st.session_state.last_result
    st.divider()
    st.header(f"Results: {result['role']}")

    comp = result["composite_score"]
    zone = result["benchmark_zone"]
    mat = result["maturity"]
    zone_color = {"success": "#1D9E75", "warning": "#BA7517", "danger": "#E24B4A"}[zone["tone"]]
    st.markdown(
        f"""
        <div style="text-align:center;padding:1rem 0 0.5rem;">
          <div style="font-size:52px;font-weight:600;color:{score_color(comp)};line-height:1;">{comp}</div>
          <div style="font-size:14px;color:gray;">composite score / 100</div>
          <div style="display:inline-block;margin-top:12px;padding:4px 14px;border-radius:999px;
               background:{zone_color}22;color:{zone_color};font-weight:500;font-size:14px;">
            {zone['label']} &middot; {zone['range']}
          </div>
        </div>
        <div style="text-align:center;padding:0.25rem 0 1.5rem;color:#444;">
          <span style="font-size:13px;color:gray;">Architecture maturity</span><br>
          <span style="font-size:18px;font-weight:600;">Level {mat['level']} of 5 — {mat['label']}</span><br>
          <span style="font-size:13px;color:#666;">{mat['blurb']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dc = result.get("decision_confidence")
    if dc:
        dc_color = score_color(dc["confidence"])
        st.markdown(
            f"""
            <div style="text-align:center;padding:0 0 1.25rem;">
              <span style="font-size:13px;color:gray;">Decision confidence</span><br>
              <span style="font-size:30px;font-weight:600;color:{dc_color};">{dc['confidence']}%</span>
              <div style="font-size:12px;color:#777;max-width:460px;margin:4px auto 0;">{dc['explanation']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Radar chart of the five dimensions
    try:
        import plotly.graph_objects as go
        radar_labels = [SCORE_LABELS[k] for k in SCORE_LABELS]
        radar_values = [result["scores"][k] for k in SCORE_LABELS]
        fig = go.Figure(go.Scatterpolar(
            r=radar_values + [radar_values[0]],
            theta=radar_labels + [radar_labels[0]],
            fill="toself",
            line=dict(color="#1D9E75"),
            fillcolor="rgba(29,158,117,0.25)",
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False, height=380, margin=dict(l=60, r=60, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass

    for key in SCORE_LABELS:
        render_score_bar(
            SCORE_LABELS[key], result["scores"][key],
            result["explanations"][key], result["evidentiary_basis"][key],
        )

    st.subheader("Highest-leverage fix")
    st.warning(result["recommendation"])

    # Evidence density
    ed = result.get("evidence_density")
    if ed and ed.get("assessed_targets", 0) > 0:
        band_color = {"weak": "#E24B4A", "moderate": "#BA7517", "strong": "#1D9E75"}.get(ed["band"], "#888")
        st.markdown(
            f"""
            <div style="border:0.5px solid #ddd;border-radius:10px;padding:14px 16px;margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;align-items:baseline;">
                <span style="font-weight:500;font-size:15px;">Evidence density</span>
                <span style="font-weight:600;font-size:18px;color:{band_color};">{ed['density']} <span style="font-size:13px;text-transform:capitalize;">({ed['band']})</span></span>
              </div>
              <div style="font-size:12.5px;color:#666;margin-top:6px;">{ed['explanation']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Duplication findings
    analysis = result.get("coverage_analysis", {})
    duplication = analysis.get("duplication", [])
    purpose_overlap = result.get("purpose_overlap", [])
    if duplication or purpose_overlap:
        st.subheader("Possible redundancy")
        for d in duplication:
            st.info(
                f"**{d['target']}** is assessed by {d['count']} stages using the same method type "
                f"({', '.join(d['stages'])}). Repeating the same kind of assessment adds candidate burden "
                "without adding much new signal — assessing it via a different method would be stronger triangulation."
            )
        for o in purpose_overlap:
            st.info(
                f"**{o['count']} stages share the purpose '{o['purpose']}'** "
                f"({', '.join(o['stages'])}). Overlapping stage purposes are the most common cause of "
                "bloated loops — check whether these could be merged or differentiated."
            )

    # Coverage heatmap
    matrix = analysis.get("matrix", [])
    stage_names = analysis.get("stage_names", [])
    if matrix and stage_names:
        st.subheader("Competency coverage heatmap")
        st.caption("Where each target is assessed across your stages. Gaps and over-coverage both show at a glance.")
        header = "| Target | " + " | ".join(stage_names) + " | Count |\n"
        header += "|---|" + "|".join([":---:"] * len(stage_names)) + "|:---:|\n"
        body = ""
        for row in matrix:
            cells = " | ".join("✅" if c else "·" for c in row["cells"])
            flag = " ⚠️" if row["count"] == 0 else (" 🔁" if row["count"] >= 3 else "")
            body += f"| {row['target']}{flag} | {cells} | {row['count']} |\n"
        st.markdown(header + body)
        st.caption("⚠️ = not assessed anywhere · 🔁 = possible duplication (3+ stages)")

    st.subheader("Competency coverage map")
    st.caption("Each value you're hiring for, the competency it translates to, and whether any stage assesses it.")
    weights_by_id, library_by_value = None, None
    from scoring_engine import load_knowledge_base
    _, library_by_value = load_knowledge_base(KB_DIR)
    for value in result["values_audited"]:
        entry = library_by_value.get(value.lower())
        competency = entry["competency"] if entry else value
        assessed_in = [
            s["name"] for s in result["stages_audited"]
            if competency.lower() in [c.lower() for c in s.get("competencies_assessed", [])]
        ]
        if assessed_in:
            st.markdown(f"✅ **{value}** → *{competency}* → assessed in: {', '.join(assessed_in)}")
        else:
            st.markdown(f"⚠️ **{value}** → *{competency}* → **not assessed anywhere**")

    for req in result.get("technical_requirements_audited", []):
        assessed_in = [
            s["name"] for s in result["stages_audited"]
            if req.lower() in [t.lower() for t in s.get("technical_assessed", [])]
        ]
        if assessed_in:
            st.markdown(f"✅ **{req}** *(domain)* → assessed in: {', '.join(assessed_in)}")
        else:
            st.markdown(f"⚠️ **{req}** *(domain)* → **not assessed anywhere**")

    st.divider()
    report_html = build_report_html(result, library_by_value)
    st.download_button(
        "⬇ Download full report (HTML)",
        data=report_html,
        file_name=f"hiring_audit_{result['role'].replace(' ', '_').lower()}.html",
        mime="text/html",
    )
    st.caption("Open the downloaded file in any browser, then use Print → Save as PDF for a PDF copy.")


# ---------- Generated architecture (distinct section) ----------
if "generated_arch" in st.session_state:
    arch = st.session_state.generated_arch
    st.divider()
    st.header(f"Recommended starting architecture: {arch['role']}")
    for note in arch["notes"]:
        st.caption(note)

    rows = "| Stage | Purpose | Method | Assesses |\n|---|---|---|---|\n"
    for s in arch["stages"]:
        rows += f"| {s['name']} | {s['purpose']} | {s['method']} | {s['assesses']} |\n"
    st.markdown(rows)

    if arch.get("onet_note"):
        st.info(arch["onet_note"])
    elif arch.get("onet_skills") == [] and "generated_arch" in st.session_state:
        st.caption("Generated from the built-in knowledge base. Add an O*NET API key and a role title to enrich with U.S. Department of Labor role data.")
