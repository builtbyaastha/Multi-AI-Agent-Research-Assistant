# Multi-Agent AI Research Assistant

## Overview

This project is a multi-agent AI research assistant designed to automate the process of gathering information, analyzing sources, generating research summaries, and reviewing the final output.

Instead of relying on a single AI model, the system uses multiple specialized agents that work together in a pipeline. Each agent is responsible for a specific task such as searching the web, extracting relevant information, writing a research report, and evaluating the quality of the generated summary.

The project was built to explore agentic AI workflows, tool integration, and automated research systems using LangGraph and LangChain.

---

## Features

* Multi-agent architecture
* Automated web search using Exa
* Web content extraction using BeautifulSoup
* Research report generation
* Automated report review and feedback
* Streamlit-based user interface
* Local LLM inference using Ollama
* Modular and extensible design

---

## System Architecture

The system follows a sequential multi-agent workflow:

User Query
→ Search Agent
→ Reader Agent
→ Writer Agent
→ Critic Agent
→ Final Research Report

### Search Agent

The Search Agent gathers recent and relevant information from the web using the Exa Search API.

Responsibilities:

* Search the web for information related to the user query
* Collect relevant sources
* Pass findings to the next stage

---

### Reader Agent

The Reader Agent processes the information returned by the Search Agent.

Responsibilities:

* Extract key information from retrieved content
* Identify important findings
* Filter unnecessary information
* Prepare context for report generation

---

### Writer Agent

The Writer Agent generates a structured research summary.

Responsibilities:

* Combine information from multiple sources
* Produce a coherent report
* Highlight important findings, methods, and trends
* Present information in a readable format

---

### Critic Agent

The Critic Agent reviews the generated report.

Responsibilities:

* Identify missing information
* Check consistency and clarity
* Suggest improvements
* Evaluate report quality

---

## Technology Stack

### Frameworks

* LangChain
* LangGraph
* Streamlit

### Search and Retrieval

* Exa Search API
* BeautifulSoup
* Requests

### Language Models

* Ollama
* Mistral

### Utilities

* Python
* dotenv
* Pydantic

---

## Project Structure

```text
Multi_Agent_System/
│
├── app.py
├── pipeline.py
├── agents.py
├── tools.py
├── requirements.txt
├── .env
│
├── screenshots/
│
└── README.md
```

---

## Screenshots

### Home Page

<img width="1915" height="1073" alt="image" src="https://github.com/user-attachments/assets/c08da6ab-3950-4789-bcdd-731414cdfebf" />


---

### Search Agent Output

<img width="1919" height="998" alt="image" src="https://github.com/user-attachments/assets/001fe496-f718-4d5f-98e2-9956cc6941e0" />


---

### Reader Agent Output

<img width="1919" height="1074" alt="image" src="https://github.com/user-attachments/assets/a22aac73-8c10-4016-8a10-1f04f8559960" />
<img width="1919" height="1003" alt="image" src="https://github.com/user-attachments/assets/358ee1b9-3b1a-431b-90e8-98f5a47e7930" />



---

### Generated Research Report

<img width="1919" height="1067" alt="image" src="https://github.com/user-attachments/assets/1cdb436f-0e5f-42ae-b450-188027b09737" />
<img width="1919" height="997" alt="image" src="https://github.com/user-attachments/assets/e61f0c30-b41b-4ff1-b4d0-f65fcba8be31" />


---

### Critic Agent Feedback

<img width="1919" height="1060" alt="image" src="https://github.com/user-attachments/assets/4d664cac-9833-460b-b2ad-5a4f191f7a56" />
<img width="1919" height="1068" alt="image" src="https://github.com/user-attachments/assets/7307be38-1a16-4b47-b10d-b462af7aec07" />


---

## Installation

### Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Multi-AI-Agent-Research-Assistant.git

cd Multi-AI-Agent-Research-Assistant
```

### Create Virtual Environment

```bash
uv venv

source .venv/bin/activate
```

### Install Dependencies

```bash
uv pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file and add:

```env
EXA_API_KEY=your_api_key
```

### Pull Ollama Model

```bash
ollama pull mistral
```

### Run the Application

```bash
streamlit run app.py
```

---

## Example Workflow

1. User enters a research topic.
2. Search Agent gathers information from the web.
3. Reader Agent extracts important details.
4. Writer Agent generates a research report.
5. Critic Agent reviews the report and provides feedback.
6. Final results are displayed through the Streamlit interface.

---

## Future Improvements

* PDF export of reports
* Research paper retrieval from ArXiv
* Long-term memory using vector databases
* Multi-document summarization
* Agent evaluation metrics
* Citation generation
* Support for additional local models

---

## What I Learned

This project helped me gain hands-on experience with:

* Agentic AI systems
* LangGraph workflows
* Tool calling
* Prompt engineering
* Local LLM deployment with Ollama
* Web search and content extraction
* Building AI applications with Streamlit

---

## Author

Aastha Sinha
