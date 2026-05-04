from google.adk.agents.llm_agent import Agent
import os
from dotenv import load_dotenv
load_dotenv()
beautifier_agent = Agent(
    model=os.getenv("MODEL_NAME"),
    name="markdown_beautifier",
    description="Cleans and structures raw documentation markdown",
    
    instruction="""
You are a markdown formatting expert.

Input: raw markdown extracted from documentation websites.

Your job:
- Remove UI junk (breadcrumbs, navigation links like "Home", "Back to top")
- Remove duplicated or irrelevant lines
- Preserve ALL actual documentation content
- Fix spacing and formatting
- Ensure proper markdown structure:
    - headings (#, ##, ###)
    - lists
    - code blocks (with backticks)
- Separate sections clearly with spacing
- Do NOT remove useful content.
- Do NOT summarize.
- Do NOT remove any content.
- Do not return your thinking.
IMPORTANT:
If you include anything other than markdown, the system will break.
Output:
Return ONLY clean, well-structured markdown.
""",
)
metadata_agent = Agent(
    model=os.getenv("MODEL_NAME"),
    name="metadata_generator",
    description="Generates llms.txt metadata from markdown",
    instruction="""
You are a documentation analyzer.

Input: clean markdown documentation.

Your job:
- Identify major sections (based on headings like ##, ###)
- Extract title
- Generate a short summary (1–2 lines)
- Extract keywords (3–6 words)

Output format (STRICT JSON):
{
    "title" : "<Content Title>", #Give a suitable title, it can be long.
    "summary" : "<short summary>",  #short summary that include everything in the content
    "keywords" : [list of keywords]
}



IMPORTANT:
- Output MUST be clean dictionary format
- Do NOT include explanations
""",
)


root_agent = Agent(
    model="gemma-4-26b-a4b-it",
    name="docs_pipeline_agent",
    description="Processes markdown into clean docs and metadata",
    instruction="""
You process documentation in two steps:
You would get raw md content as user input.

Step 1:
Clean the raw markdown using the markdown_beautifier agent.

Step 2:
Use the cleaned markdown as input to metadata_generator agent.

Return:
1. Clean markdown
2. Generated llms.txt content
in Dictionary :
OUTPUT EXAMPLE:
{
  "clean_md" : "<md content",
  "meta_json" : {<nested dictionary}"
}
Do not skip steps.
""",
    sub_agents=[beautifier_agent, metadata_agent],
)
