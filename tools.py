from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from exa_py import Exa
import os
from dotenv import load_dotenv


load_dotenv()

exa = Exa(api_key=os.getenv("EXA_API_KEY"))

@tool
def WebSearch(query: str) -> str:
    """
    Search the web for recent and reliable information on a topic.
    Return title, URL, and summary of content.
    """

    results = exa.search(
        query,
        num_results=5
    )

    out = []
    for r in results.results:
        text = r.text or "no text available"
        out.append(f"Title: {r.title}\n"
                   f"URL: {r.url}\n"
                   f"Summary: {text[:200]}\n")
        
    return "\n-----\n".join(out)



@tool 
def web_scrape(url: str) -> str:
    """
    Scrape the content of a web page and return clean text.
    """
    try:
        response = requests.get(url, timeout=7, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:2000]  # Limit to first 2000 characters 
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"
    
    


    