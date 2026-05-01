import requests
import json
from wiki_tool import fetch_wikipedia_summary

def run_gap_analyst(weak_topic: str):
    print(f"Gap Analyst received weak topic: {weak_topic}")
    
    # 1. Use the tool to research the knowledge gap
    print("Gap Analyst is researching via Wikipedia...")
    wiki_data = fetch_wikipedia_summary(weak_topic)
    
    # 2. System prompt for an educational researcher
    system_prompt = """You are an expert Educational Curriculum Researcher (Gap Analyst). 
    You will receive an academic topic where a student has shown a knowledge gap.
    Using ONLY the provided Wikipedia data, output exactly 3 concise bullet points summarizing the core concepts to help the student catch up. 
    Do NOT invent or hallucinate any information."""
    
    user_prompt = f"Topic: {weak_topic}\nWikipedia Data: {wiki_data}"
    
    # 3. Send to local Ollama
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3:8b",
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "stream": False
    }
    
    print("Gap Analyst is compiling the brief...\n")
    response = requests.post(url, json=payload)
    
    # 4. Output the result for the next agent (Question Generator)
    if response.status_code == 200:
        result = response.json()['response']
        print("--- Knowledge Gap Brief ---")
        print(result)
    else:
        print("Error connecting to Ollama.")

# --- Test the Agent ---
if __name__ == "__main__":
    # Simulating receiving a weak topic from the Assessment Agent
    run_gap_analyst("Calculus")