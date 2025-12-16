"""
10-Minute Consistency Coach

A calm, minimal fitness-planning agent that generates a short,
safe, and doable daily workout based on a user’s context.

Design principles:
- Low friction (decide in under 30 seconds)
- Safety-first (constraints and soreness respected)
- Consistency over intensity
- Explainable decisions ("Why this plan?")
"""

from datetime import date
import streamlit as st


# ------------------------------------------------------------
# App configuration
# ------------------------------------------------------------
# Sets basic UI defaults so the app feels focused and uncluttered.
st.set_page_config(
    page_title="10-Minute Consistency Coach",
    page_icon="🧘",
    layout="centered",
)


# ------------------------------------------------------------
# App introduction
# ------------------------------------------------------------
# This section orients the user immediately:
# What is this app and what value does it provide?
st.title("10-Minute Consistency Coach")
st.write("Small daily movement. Big long-term impact.")
st.caption(f"Today: {date.today().isoformat()}")


# ------------------------------------------------------------
# User context inputs
# ------------------------------------------------------------
# Each input maps directly to the agent's decision logic.
# No input exists unless it changes the resulting plan.
st.markdown("## Your inputs")

goal = st.selectbox(
    "Goal",
    ["Strength", "Mobility", "Fat loss"],
)

minutes = st.selectbox(
    "Time today",
    [10, 15, 20],
)

energy = st.selectbox(
    "Energy today",
    ["Low", "Normal", "High"],
)

equipment = st.selectbox(
    "Equipment",
    ["None", "Resistance band", "Dumbbells"],
)

constraints = st.multiselect(
    "Constraints",
    ["Knee pain", "Back pain", "No jumping", "Quiet (apartment-friendly)"],
)

sore = st.multiselect(
    "Sore today (avoid)",
    ["Chest/Shoulders", "Legs", "Core/Back"],
)


# ------------------------------------------------------------
# Run agent action
# ------------------------------------------------------------
# The button represents the moment the agent evaluates the context
# and generates a plan.
generate = st.button("Generate today’s plan", use_container_width=True)


# ------------------------------------------------------------
# Output (current implementation)
# ------------------------------------------------------------
# For now, this displays the interpreted user context in a structured way.
# This confirms that the agent receives clean, well-defined input data.
if generate:
    st.markdown("## Today’s plan")

    st.write(
        {
            "goal": goal,
            "minutes": minutes,
            "energy": energy,
            "equipment": equipment,
            "constraints": constraints,
            "sore": sore,
        }
    )

    # Placeholder text describing the shape of the output.
    # The final version will replace this with a generated plan.
    st.markdown(
        """
### Plan structure
- Warm-up (2 minutes)
- Main block (goal-aligned, time-aware)
- Cool-down (1 minute)
- **Why this plan?** (explainable rationale)
- Safety note
"""
    )
