import requests
from typing import Optional

def fetch_wikipedia_summary(topic: str) -> Optional[str]:
    """
    Fetches a brief summary of a given educational topic using the public Wikipedia API.

    Args:
        topic (str): The specific subject or keyword to search for on Wikipedia.

    Returns:
        Optional[str]: A string containing the extracted Wikipedia extract if successful.
                       Returns None if an error occurs.
    """
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        if "extract" in data:
            return data["extract"]
        return "Topic not found on Wikipedia."
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching data: {e}"

# --- Test the tool ---
if __name__ == "__main__":
    print("Testing the Wikipedia Tool...")
    result = fetch_wikipedia_summary("Photosynthesis")
    print(result)