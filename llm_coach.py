import requests
import time

class LLMFitnessCoach:
    def __init__(self, model="llama3.2:3b"):
        self.model = model
        self.base_url = "http://localhost:11434"
        print(f"🤖 Coach initialized with {model}")
    
    def is_available(self):
        """Check if Ollama is REALLY available"""
        try:
            # Quick test
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            available = response.status_code == 200
            print(f"🔍 is_available() check: {available}")
            return available
        except Exception as e:
            print(f"🔍 is_available() error: {e}")
            return False
    
    def enhance_rationale(self, inputs, exercises):
        """Generate rationale with Ollama"""
        print(f"🎯 enhance_rationale called with {len(exercises)} exercises")
        
        if not self.is_available():
            print("❌ Ollama not available in enhance_rationale")
            return None
        
        try:
            prompt = f"""As a fitness coach, explain this workout:

Goal: {inputs.get('goal')}
Time: {inputs.get('time')} minutes
Energy: {inputs.get('energy')}
Exercises: {', '.join(exercises[:3])}

Write a brief, encouraging explanation (2 sentences max)."""
            
            print(f"📤 Sending prompt to Ollama...")
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=15  # Give it more time
            )
            
            print(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                print(f"✅ AI generated: '{text[:80]}...'")
                return text
            else:
                print(f"❌ Ollama error: {response.status_code} - {response.text[:100]}")
                return None
                
        except Exception as e:
            print(f"❌ Exception in enhance_rationale: {e}")
            return None