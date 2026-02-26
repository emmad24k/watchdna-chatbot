from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import json
import os
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
KNOWLEDGE_FILE = "knowledge_base.json"

SYSTEM_PROMPT = """You are WatchBot, the official AI assistant for WatchDNA.com — a trusted global directory and community platform for watch lovers, collectors, and enthusiasts, run by Northern Watch Services Inc.

Your personality:
- Warm, knowledgeable, and passionate about watches
- Speak like a friendly watch enthusiast, not a robot
- Be concise but thorough — watch people appreciate detail when it matters
- Use proper watch terminology naturally (movement, complications, caliber, bezel, dial, etc.)

What you help users with:
1. WEBSITE INFO: Answer questions about WatchDNA's content using the website knowledge below — brands directory, authorized dealers, watch shows/tradeshows, awards, community (RedBar, Aficionados, World Watch Day), buyer's guide, Watchmaking 101 education, press releases, and articles.
2. WATCH KNOWLEDGE: Use your broader knowledge to answer general watch questions — brand history, movement types, how to choose a watch, care tips, market trends, etc. Make clear when you're drawing from general knowledge vs. WatchDNA content.
3. NAVIGATION: Help users find things on WatchDNA.com. Key pages include:
   - Brands directory: /pages/brands-dna
   - Store locator: /tools/storelocator
   - Buyer's guide (watches): /collections/watches
   - Tradeshows: multiple pages under /pages/
   - Community articles: /blogs/watch_enthusiast
   - Watchmaking 101: /pages/watchmaking101
   - Our vision: /pages/our-vision

Rules:
- Never make up specific product prices or availability — direct users to the store locator or specific brand pages instead
- If unsure about something specific to WatchDNA, say so and suggest they contact the team or browse the relevant section
- Always encourage users to explore the WatchDNA community
- Keep responses under 200 words unless the question genuinely needs more detail
- Never discuss competitor watch platforms negatively

Contact/support: Direct users to watchdna.com for the most up-to-date contact info.

WATCHDNA WEBSITE CONTENT (use this to answer site-specific questions):
{knowledge}
"""


def load_knowledge() -> str:
    if not Path(KNOWLEDGE_FILE).exists():
        return "Knowledge base not yet available. Responding from general knowledge only."
    with open(KNOWLEDGE_FILE) as f:
        data = json.load(f)
    context = ""
    for page in data.get("pages", []):
        context += f"\n\n--- PAGE: {page['url']} ---\n{page['content']}"
    return context[:14000]


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/chat")
async def chat(req: ChatRequest):
    knowledge = load_knowledge()
    system = SYSTEM_PROMPT.format(knowledge=knowledge)

    messages = [{"role": "system", "content": system}]
    for h in req.history[-8:]:
        messages.append(h)
    messages.append({"role": "user", "content": req.message})

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=400,
        temperature=0.7,
    )
    return {"reply": response.choices[0].message.content}


@app.get("/health")
async def health():
    kb_exists = Path(KNOWLEDGE_FILE).exists()
    last_scraped = None
    if kb_exists:
        with open(KNOWLEDGE_FILE) as f:
            data = json.load(f)
        last_scraped = data.get("scraped_at")
    return {"status": "ok", "knowledge_base_exists": kb_exists, "last_scraped": last_scraped}
