"""
10-Minute Consistency Coach - Simple AI Version
AI works quietly in the background, no indicators
"""

import streamlit as st
import json
from datetime import datetime
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import AI, but don't worry if it fails
try:
    from llm_coach import LLMFitnessCoach
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False
    print("Note: AI features not available")

# Page config - Keep your dark theme
st.set_page_config(
    page_title="10-Minute Consistency Coach",
    page_icon="🏋️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Dark theme CSS (your original)
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stButton > button {
        background-color: #FF4B4B;
        color: white;
    }
    hr {
        border-color: #444;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Simple header - exactly like your original
    st.title("10-Minute Consistency Coach")
    st.caption("A calm, minimal fitness-planning agent")
    
    # Your original input section
    st.subheader("Your details today")
    
    col1, col2 = st.columns(2)
    
    with col1:
        goal = st.selectbox("Goal:", ["Strength", "Mobility", "Fat loss"])
        time_today = st.radio("Time today:", [10, 15, 20], horizontal=True)
        energy = st.select_slider("Energy today:", ["Low", "Normal", "High"])
    
    with col2:
        equipment = st.selectbox("Equipment:", 
                                ["None", "Resistance band", "Dumbbells", "Chair"])
        constraints = st.multiselect("Constraints:", 
                                    ["Knee pain", "Back pain", "No jumping", "Quiet"])
        soreness = st.multiselect("Sore today (avoid):", 
                                 ["Chest/Shoulders", "Legs", "Core/Back"])
    
    # Single generate button
    if st.button("Generate Today's Plan", type="primary", use_container_width=True):
        with st.spinner("Creating your plan..."):
            # Prepare inputs
            inputs = {
                'goal': goal,
                'time': time_today,
                'energy': energy,
                'equipment': equipment,
                'constraints': constraints,
                'soreness': soreness
            }
            
            # Get exercises (use your existing logic here)
            # For now, simple placeholder
            exercises = get_exercises(goal, constraints, soreness, equipment)
            
            # Create plan
            plan = create_plan(inputs, exercises)
            
            # Generate rationale - AI works silently if available
            rationale = generate_rationale(inputs, exercises)
            
            # Display results
            st.divider()
            
            # Plan header
            st.subheader(f"Today's {time_today}-minute plan")
            st.caption(f"{goal} focus • {energy} energy")
            
            # Show plan
            st.markdown(plan)
            
            # Show rationale
            st.subheader("Why this plan?")
            st.info(rationale)
            
            # Safety note (your original)
            st.caption("⚠️ **Safety Note**: This is not medical advice. Listen to your body.")
            
            # Simple download
            st.download_button(
                "Download Plan",
                data=json.dumps({
                    "plan": plan,
                    "rationale": rationale,
                    "inputs": inputs
                }, indent=2),
                file_name="workout_plan.json"
            )


def get_exercises(goal, constraints, soreness, equipment):
    """Get exercises - REPLACE WITH YOUR EXISTING LOGIC"""
    # This is just placeholder - use your actual exercise selection logic
    exercises_by_goal = {
        "Strength": ["Wall Push-ups", "Glute Bridges", "Chair Squats", "Plank"],
        "Mobility": ["Gentle March", "Shoulder Rolls", "Hip Circles", "Cat-Cow"],
        "Fat loss": ["March in Place", "Knee Raises", "Speed Skaters", "Leg Lifts"]
    }
    
    exercises = exercises_by_goal.get(goal, [])
    
    # Simple filtering
    filtered = []
    for ex in exercises:
        ex_lower = ex.lower()
        skip = False
        
        if "knee" in str(constraints).lower() and "squat" in ex_lower:
            skip = True
        if "quiet" in str(constraints).lower() and "jump" in ex_lower:
            skip = True
            
        if not skip:
            filtered.append(ex)
    
    return filtered[:4]


def create_plan(inputs, exercises):
    """Create workout plan"""
    if not exercises:
        return "No suitable exercises found. Please adjust your constraints."
    
    time_main = inputs['time'] - 3
    
    plan = f"""
**Warm-up** (2 minutes)
• Gentle marching in place: 60s
• Shoulder rolls: 30s forward, 30s backward

**Main workout** ({time_main} minutes)
"""
    
    # Equal time per exercise
    seconds_per_ex = (time_main * 60) // len(exercises)
    
    for ex in exercises:
        plan += f"• **{ex}**: {seconds_per_ex}s\n"
    
    plan += f"""
**Cool-down** (1 minute)
• Hamstring stretch: 30s each side
• Chest opener: 30s
"""
    
    return plan


def generate_rationale(inputs, exercises):
    """Generate rationale - AI works silently if available"""
    # Try AI first (silently)
    if AI_AVAILABLE:
        try:
            coach = LLMFitnessCoach()
            if coach.is_available():
                rationale = coach.enhance_rationale(inputs, exercises)
                # Check if AI actually returned something good
                if rationale and rationale.lower() != "none" and len(rationale.strip()) > 10:
                    return rationale
                # If AI returned "None" or something too short, fall back
        except:
            # AI failed - fall through to basic rationale
            pass
    
    # Basic rationale (no AI or AI failed)
    parts = []
    
    if inputs['energy'].lower() == 'low':
        parts.append("gentle for low energy")
    elif inputs['energy'].lower() == 'high':
        parts.append("energetic for high energy")
    else:
        parts.append("balanced for normal energy")
    
    if inputs['constraints']:
        parts.append(f"respects your constraints")
    
    if inputs['soreness']:
        parts.append(f"avoids sore areas")
    
    if inputs['goal']:
        parts.append(f"focuses on {inputs['goal'].lower()}")
    
    rationale = "This plan is " + ", ".join(parts) if parts else "tailored to your needs"
    return f"{rationale}. Perfect for a {inputs['time']}-minute session."


if __name__ == "__main__":
    main()