import asyncio
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv
from dedalus_labs.utils.streaming import stream_async

load_dotenv()

async def research_query(query):
    client = AsyncDedalus()
    runner = DedalusRunner(client)

    result = await runner.run(
        input= query,
        model="openai/gpt-4.1",
        mcp_servers=[
            "joerup/exa-mcp",        # Semantic search engine
            "tsion/brave-search-mcp",  # Privacy-focused web search
            "dallinger/wikipedia-mcp",  # Wikipedia search
            "modelcontextprotocol/google-search",  # Google search
            "modelcontextprotocol/github"  # GitHub profiles
        ]
    )

    return (f"Web Search Results:\n{result.final_output}")

if __name__ == "__main__":
    result = asyncio.run(research_query("""Search for information about John Cole from UT Dallas. Look for:
        1. Professional profiles on GitHub, personal websites, or portfolios
        2. Academic publications or research papers
        3. News articles or press mentions
        4. Social media profiles (Twitter, etc.)
        5. Any public professional achievements or projects
        Focus on publicly available information only."""))
    print(result)