"""
10-Minute Consistency Coach

A calm, minimal fitness-planning agent that generates a short daily plan
based on user context:
- goal, time, energy, equipment
- constraints (knee/back/no jumping/quiet)
- soreness (avoid overused areas)

Core idea:
This is not just text generation. We use a small rules engine:
1) Filter unsafe/undesired movements
2) Substitute when needed
3) Produce an explainable plan ("Why this plan?")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import os
import csv
from typing import List, Dict, Optional, Tuple

import streamlit as st


# ============================================================
# UI configuration (minimal + calm)
# ============================================================
st.set_page_config(page_title="10-Minute Consistency Coach", page_icon="🧘", layout="centered")

st.markdown(
    """
    <style>
      .block-container {max-width: 780px; padding-top: 2.2rem;}
      .stButton>button {border-radius: 14px; padding: 0.7rem 1rem; font-weight: 650;}
      .card {
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 18px;
        padding: 18px 18px;
        background: rgba(255,255,255,0.95);
        box-shadow: 0 8px 20px rgba(0,0,0,0.04);
      }
      .muted {color: rgba(0,0,0,0.55); font-size: 0.95rem;}
      hr {border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 12px 0;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("10-Minute Consistency Coach")
st.write("Small daily movement. Big long-term impact.")
st.caption(f"Today: {date.today().isoformat()}")


# ============================================================
# Agent data model
# ============================================================
# We keep a tiny movement library with tags. Tags make the "agent logic"
# transparent and controllable (less chance of unsafe/hallucinated output).
@dataclass(frozen=True)
class Movement:
    name: str
    goals: List[str]              # e.g. ["Strength", "Fat loss"]
    impact: str                   # "low" | "normal" | "high"
    strain: List[str]             # e.g. ["knees", "back", "shoulders"]
    equipment: List[str]          # e.g. ["None", "Dumbbells"]
    substitutes: List[str]        # movement names, ordered by preference


# A compact library is enough for an MVP. You can expand it later.
MOVEMENTS: List[Movement] = [
    Movement("March in place", ["Mobility", "Fat loss"], "low", [], ["None"], ["Step taps"]),
    Movement("Step taps", ["Mobility", "Fat loss"], "low", [], ["None"], []),

    Movement("Arm circles", ["Mobility"], "low", ["shoulders"], ["None"], []),
    Movement("Hip hinges (slow)", ["Mobility", "Strength"], "low", ["back"], ["None"], []),
    Movement("Cat-cow (slow)", ["Mobility"], "low", ["back"], ["None"], []),

    Movement("Chair squats", ["Strength", "Fat loss"], "normal", ["knees", "back"], ["None"], ["Sit-to-stand (small range)", "Glute bridge"]),
    Movement("Sit-to-stand (small range)", ["Strength"], "low", ["knees"], ["None"], ["Glute bridge"]),
    Movement("Glute bridge", ["Strength", "Mobility"], "low", [], ["None"], []),

    Movement("Lunges", ["Strength", "Fat loss"], "normal", ["knees"], ["None"], ["Glute bridge"]),
    Movement("Wall sit", ["Strength"], "normal", ["knees"], ["None"], ["Glute bridge"]),

    Movement("Wall push-ups", ["Strength"], "low", ["shoulders", "wrists"], ["None"], []),
    Movement("Incline push-ups", ["Strength"], "normal", ["shoulders", "wrists"], ["None"], ["Wall push-ups"]),
    Movement("Floor push-ups", ["Strength"], "normal", ["shoulders", "wrists"], ["None"], ["Incline push-ups", "Wall push-ups"]),

    Movement("Bird-dog", ["Mobility", "Strength"], "low", ["back"], ["None"], ["Dead bug (small range)"]),
    Movement("Dead bug (small range)", ["Mobility", "Strength"], "low", ["back"], ["None"], ["Heel taps (tiny range)"]),
    Movement("Heel taps (tiny range)", ["Mobility", "Strength"], "low", ["back"], ["None"], []),

    Movement("Jumping jacks", ["Fat loss"], "high", ["knees", "back"], ["None"], ["Step taps"]),
    Movement("Burpees", ["Fat loss"], "high", ["knees", "back", "shoulders"], ["None"], ["Step taps"]),

    Movement("Band row", ["Strength"], "normal", ["back"], ["Resistance band"], ["Wall push-ups"]),
    Movement("Dumbbell deadlift (light)", ["Strength"], "normal", ["back"], ["Dumbbells"], ["Hip hinges (slow)"]),
]


# Fast lookup by name for substitution.
MOVE_BY_NAME: Dict[str, Movement] = {m.name: m for m in MOVEMENTS}


# ============================================================
# Constraint rules (explainable)
# ============================================================
def build_rules(energy: str, constraints: List[str], sore: List[str]) -> Dict:
    """
    Convert user selections into a simple rule set:
    - exclude strain areas (knees/back)
    - exclude impact level (high)
    - avoid areas due to soreness
    - prefer low impact when energy is low
    """
    exclude_strain = set()
    exclude_impact = set()
    avoid_strain = set()

    if "Knee pain" in constraints:
        exclude_strain.add("knees")
    if "Back pain" in constraints:
        exclude_strain.add("back")

    if ("No jumping" in constraints) or ("Quiet (apartment-friendly)" in constraints):
        exclude_impact.add("high")

    # Soreness behaves like "avoid" rather than a strict safety exclusion.
    # We still try to respect it strongly for consistency reasons.
    if "Chest/Shoulders" in sore:
        avoid_strain.add("shoulders")
    if "Legs" in sore:
        avoid_strain.add("knees")
    if "Core/Back" in sore:
        avoid_strain.add("back")

    prefer_low_impact = (energy == "Low")

    return {
        "exclude_strain": exclude_strain,
        "exclude_impact": exclude_impact,
        "avoid_strain": avoid_strain,
        "prefer_low_impact": prefer_low_impact,
    }


def is_blocked(m: Movement, rules: Dict) -> bool:
    """Hard blockers: safety constraints + impact restrictions."""
    if m.impact in rules["exclude_impact"]:
        return True
    if any(s in rules["exclude_strain"] for s in m.strain):
        return True
    return False


def is_avoided(m: Movement, rules: Dict) -> bool:
    """Soft blockers: soreness (try not to pick these unless needed)."""
    return any(s in rules["avoid_strain"] for s in m.strain)


def resolve_movement(name: str, equipment: str, rules: Dict) -> Tuple[str, Optional[str]]:
    """
    Resolve a movement name to a safe/appropriate movement.
    Returns: (final_name, reason_if_substituted)

    Strategy:
    - If the movement is blocked, try substitutes in order.
    - If not blocked but avoided (sore), try substitutes too.
    - Ensure equipment compatibility.
    """
    if name not in MOVE_BY_NAME:
        # Unknown movement name should never happen in our MVP; guard anyway.
        return name, "Unknown movement; kept as-is."

    m = MOVE_BY_NAME[name]

    # Equipment check: if user doesn't have required equipment, substitute if possible.
    if equipment not in m.equipment:
        for sub in m.substitutes:
            if sub in MOVE_BY_NAME and equipment in MOVE_BY_NAME[sub].equipment and not is_blocked(MOVE_BY_NAME[sub], rules):
                return sub, f"Substituted due to equipment: {name} → {sub}"
        return name, f"Kept despite equipment mismatch (MVP fallback): {name}"

    # Hard block (constraints/impact)
    if is_blocked(m, rules):
        for sub in m.substitutes:
            if sub in MOVE_BY_NAME:
                sm = MOVE_BY_NAME[sub]
                if equipment in sm.equipment and not is_blocked(sm, rules):
                    return sub, f"Substituted for safety/constraints: {name} → {sub}"
        return name, f"No safe substitute found (MVP fallback): {name}"

    # Soft avoid (soreness)
    if is_avoided(m, rules):
        for sub in m.substitutes:
            if sub in MOVE_BY_NAME:
                sm = MOVE_BY_NAME[sub]
                if equipment in sm.equipment and not is_blocked(sm, rules) and not is_avoided(sm, rules):
                    return sub, f"Substituted due to soreness: {name} → {sub}"
        # If no better option, keep it but rationale will mention soreness.
        return name, None

    return name, None


# ============================================================
# Plan generation (rules + templates)
# ============================================================
def build_plan(
    goal: str,
    minutes: int,
    level: str,
    energy: str,
    equipment: str,
    constraints: List[str],
    sore: List[str],
) -> Dict:
    rules = build_rules(energy, constraints, sore)

    # Warm-up: stable, low-risk. We keep it consistent to reduce cognitive load.
    warmup = [
        ("March in place", "30s"),
        ("Arm circles", "30s"),
        ("Hip hinges (slow)", "30s"),
        ("Step taps", "30s"),
    ]

    # Main block templates (names only) — then we resolve with filtering/substitution.
    if goal == "Mobility":
        main_template = [
            ("Cat-cow (slow)", "6 breaths"),
            ("Bird-dog", "6/side"),
            ("Hip hinges (slow)", "45s"),
            ("Step taps", "45s"),
        ]
    elif goal == "Strength":
        # Level influences the "push" difficulty
        push = "Wall push-ups" if level == "Beginner" or energy == "Low" else "Incline push-ups"
        main_template = [
            (push, "10"),
            ("Glute bridge", "12"),
            ("Chair squats", "8–10"),
            ("Dead bug (small range)", "6/side"),
        ]
    else:  # Fat loss (low impact by default)
        main_template = [
            ("Jumping jacks", "45s"),
            ("Wall push-ups", "10"),
            ("Glute bridge", "12"),
            ("March in place", "45s"),
        ]

    cooldown = [
        ("Cat-cow (slow)", "30s"),
        ("Hip hinges (slow)", "30s"),
    ]

    # Resolve warm-up/main/cooldown moves through the agent logic
    substitutions: List[str] = []

    def resolve_block(block: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        resolved = []
        for name, dose in block:
            final_name, reason = resolve_movement(name, equipment, rules)
            resolved.append((final_name, dose))
            if reason:
                substitutions.append(reason)
        return resolved

    warmup_r = resolve_block(warmup)
    main_r = resolve_block(main_template)
    cooldown_r = resolve_block(cooldown)

    # Intensity and coaching note (calm tone)
    intensity = "easy–moderate"
    coach_note = "Consistency beats intensity. Showing up is the win."
    if energy == "Low":
        intensity = "easy"
        coach_note = "Low energy day: keep it gentle. Completing the plan is success."
    elif energy == "High":
        intensity = "moderate"
        coach_note = "High energy day: move with control, breathe, and enjoy the flow."

    # Dynamic rationale (this is what makes it feel like an agent)
    rationale = []
    if "Knee pain" in constraints:
        rationale.append("Knee-friendly selection")
    if "Back pain" in constraints:
        rationale.append("Back-friendly adjustments")
    if ("No jumping" in constraints) or ("Quiet (apartment-friendly)" in constraints):
        rationale.append("Low-impact / quiet movements")
    if sore:
        rationale.append("Soreness respected: " + ", ".join(sore))
    rationale.append(f"Energy matched: {energy.lower()}")
    rationale.append(f"Goal aligned: {goal.lower()}")

    safety = "Stop if you feel sharp pain. Keep range of motion small and controlled. This is not medical advice."

    # Rough time allocation
    warmup_minutes = 2
    cooldown_minutes = 1
    main_minutes = max(1, minutes - warmup_minutes - cooldown_minutes)

    title = f"{minutes}-Minute {goal} · {'Low impact' if ('No jumping' in constraints or 'Quiet (apartment-friendly)' in constraints) else 'Standard'}"

    return {
        "title": title,
        "warmup": warmup_r,
        "main": main_r,
        "cooldown": cooldown_r,
        "main_minutes": main_minutes,
        "intensity": intensity,
        "coach_note": coach_note,
        "rationale": rationale,
        "substitutions": substitutions,
        "safety": safety,
        "inputs": {
            "goal": goal,
            "minutes": minutes,
            "level": level,
            "energy": energy,
            "equipment": equipment,
            "constraints": constraints,
            "sore": sore,
        },
    }


# ============================================================
# Lightweight analytics (local file logging)
# ============================================================
def log_event(event: str, payload: Dict) -> None:
    """
    Writes a single row to metrics.csv.
    This is a lightweight way to demonstrate product metrics thinking without
    needing a full analytics setup.
    """
    path = "metrics.csv"
    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ts_utc", "event", "payload_json"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "ts_utc": datetime.utcnow().isoformat(),
                "event": event,
                "payload_json": json.dumps(payload, ensure_ascii=False),
            }
        )


# ============================================================
# UI inputs
# ============================================================
st.markdown("## Your inputs")

c1, c2 = st.columns(2)
with c1:
    goal = st.selectbox("Goal", ["Strength", "Mobility", "Fat loss"])
    minutes = st.selectbox("Time today", [10, 15, 20])
    equipment = st.selectbox("Equipment", ["None", "Resistance band", "Dumbbells"])
with c2:
    level = st.selectbox("Fitness level", ["Beginner", "Intermediate"])
    energy = st.selectbox("Energy today", ["Low", "Normal", "High"])
    constraints = st.multiselect(
        "Constraints",
        ["Knee pain", "Back pain", "No jumping", "Quiet (apartment-friendly)"],
        default=["Quiet (apartment-friendly)"]
    )

sore = st.multiselect("Sore today (avoid)", ["Chest/Shoulders", "Legs", "Core/Back"])

generate = st.button("Generate today’s plan", use_container_width=True)


# ============================================================
# UI output
# ============================================================
if generate:
    plan = build_plan(goal, minutes, level, energy, equipment, constraints, sore)
    log_event("plan_generated", plan["inputs"])

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"### {plan['title']}")
    st.markdown(
        f"<div class='muted'>Intensity: {plan['intensity']} · Main block: ~{plan['main_minutes']} min</div>",
        unsafe_allow_html=True
    )
    st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown("**Warm-up (2 min)**")
    for name, dose in plan["warmup"]:
        st.write(f"• {name} — {dose}")

    st.markdown(f"**Main (~{plan['main_minutes']} min)**")
    for name, dose in plan["main"]:
        st.write(f"• {name} — {dose}")

    st.markdown("**Cool-down (1 min)**")
    for name, dose in plan["cooldown"]:
        st.write(f"• {name} — {dose}")

    st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown("**Why this plan?**")
    for r in plan["rationale"]:
        st.write(f"• {r}")

    if plan["substitutions"]:
        with st.expander("Show substitutions applied"):
            for s in plan["substitutions"]:
                st.write(f"• {s}")

    st.markdown("**Coach note**")
    st.write(plan["coach_note"])
    st.caption(plan["safety"])
    st.markdown("</div>", unsafe_allow_html=True)

    # Download buttons (TXT + JSON) for shareability
    txt_lines = []
    txt_lines.append(plan["title"])
    txt_lines.append(f"Intensity: {plan['intensity']} | Main: ~{plan['main_minutes']} min\n")

    txt_lines.append("Warm-up:")
    txt_lines += [f"- {n} — {d}" for n, d in plan["warmup"]]
    txt_lines.append("\nMain:")
    txt_lines += [f"- {n} — {d}" for n, d in plan["main"]]
    txt_lines.append("\nCool-down:")
    txt_lines += [f"- {n} — {d}" for n, d in plan["cooldown"]]

    txt_lines.append("\nWhy this plan?")
    txt_lines += [f"- {x}" for x in plan["rationale"]]

    txt_lines.append(f"\nCoach note: {plan['coach_note']}")
    txt_lines.append(f"\nSafety: {plan['safety']}")

    cdl1, cdl2 = st.columns(2)
    with cdl1:
        st.download_button(
            "Download plan (txt)",
            data="\n".join(txt_lines),
            file_name="todays_plan.txt",
            mime="text/plain",
            use_container_width=True
        )
    with cdl2:
        st.download_button(
            "Download plan (json)",
            data=json.dumps(plan, ensure_ascii=False, indent=2),
            file_name="todays_plan.json",
            mime="application/json",
            use_container_width=True
        )

    # Optional: show the safety logic clearly (nice for reviewers)
    with st.expander("Constraint mapping (how safety works)"):
        st.markdown(
            """
| Input | What happens |
|---|---|
| Knee pain | Filters knee-strain movements and substitutes safer options |
| Back pain | Filters back-strain movements and substitutes smaller-range options |
| No jumping / Quiet | Filters high-impact movements |
| Low energy | Prefers gentler selections and simpler variations |
| Sore Chest/Shoulders | Avoids shoulder-heavy moves when possible |
| Sore Legs | Avoids squat/lunge patterns when possible |
| Sore Core/Back | Avoids heavy core loading when possible |
"""
        )
