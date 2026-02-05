import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "mistralai/mistral-7b-instruct"


def generate_cover_letter(job, profile, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    prompt = f"""
Write a concise, tailored cover letter.

Rules:
- 2 paragraphs
- 70–90 words
- Human tone
- No placeholders

Candidate:
Name: {profile["name"]}
Headline: {profile["headline"]}
Skills: {", ".join(profile["skills"])}

Job:
Title: {job["title"]}
Company: {job["company"]}
Description: {job["summary"]}
"""

    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
        max_tokens=200,
    )

    text = res.choices[0].message.content.strip()

    fname = f"{job['company']}__{job['title']}.txt".replace(" ","_")

    path = os.path.join(output_dir,fname)

    with open(path,"w") as f:
        f.write(text)

    return path
