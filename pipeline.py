from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain

def run_research_pipeline(topic : str) -> dict:
    state = {}
    
    print("\n" + " = "*50)
    print(" Step 1 - Search Agent: Gathering recent information on the topic")
    print(" = "*50 + "\n")
    #-----------------------------------------------------Step 1 - Search Agent------------------------------------------------------------
    search_agent = build_search_agent()
    
    search_result = search_agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": f"Search for recent and reliable information on the topic: {topic}"
        }
    ]
    })
    state["search_result"] = search_result['messages'][-1].content
    
    print("\n search result ", state["search_result"][:500], "...\n")
    
    # ---------------------------------------------------step 2 - reader agent-----------------------------------------------------------
    print("\n" + " = "*50)
    print(" Step 2 - Reader Agent: Extracting relevant information from search results")
    print(" = "*50 + "\n")
    
    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": f"""Based on the following search results about '{topic}', extract the most relevant information that would help in writing a research summary.

            Focus on:
            - key findings
            - important models/methods
            - challenges
            - future directions

            Search Results:
            {state['search_result'][:800]}
            """
        }
    ]
    })
    
    state["reader_result"] = reader_result['messages'][-1].content 
    
    state["scraped_content"] = reader_result['messages'][-1].content
    print("\n reader result ", state["scraped_content"], "...\n")
    
    #---------------------------------------------------------step 3 - writer chain--------------------------------------------------------
    print("\n" + " = "*50)
    print(" Step 3 - Writer Chain: Writing a comprehensive research summary")
    print(" = "*50 + "\n")
    
    research_combined_content = f"Search Results:\n{state['search_result'][:300]}...\n\nExtracted Information:\n{state['scraped_content'][:800]}..."
    
    
    state["report"] = writer_chain.invoke({
        "query" : topic,
        "text": research_combined_content
    })
    
    print("\n Final Research Summary:\n", state["report"][:1000], "...\n")
    
    #---------------------------------------------------------step 4 - critic chain-------------------------------------------------------
    print("\n" + " = "*50)
    print(" Step 4 - Critic Chain: Evaluating the quality of the research summary")
    print(" = "*50 + "\n")
    
    state["feedback"] = critic_chain.invoke({
        "query": topic,
        "text": research_combined_content,
        "summary": state["report"]
    })
    
    print("\n Critic Feedback:\n", state["feedback"], "\n")
    
    return state

    
if __name__ == "__main__":
    topic = input("Enter a research topic: ")
    run_research_pipeline(topic)