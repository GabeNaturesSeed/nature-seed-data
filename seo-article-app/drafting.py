"""
Article Draft Generator for Nature's Seed.

Uses Claude API to generate SEO-optimized article drafts with proper structure,
internal linking, product mentions, and image placeholders.
"""

import os
import json
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Nature's Seed brand voice guidelines (from natures-seed-brand skill)
BRAND_CONTEXT = """
Nature's Seed Brand Voice:
- Tone: Knowledgeable, helpful, approachable. We're the trusted neighbor who happens
  to be a seed expert.
- Never pushy or salesy. Educate first, recommend products naturally.
- Use "we" for Nature's Seed, "you" for the reader.
- Speak with authority on seed science but keep it accessible.
- Regional awareness: acknowledge climate zones, soil types, local conditions.
- Action-oriented: give readers clear next steps.

Product Categories:
- Lawn Seed (Northern, Southern, Transitional, Water-Wise, Sports Turf)
- Pasture Seed (Horse, Cattle, Goat, Sheep, Northern/Southern/Transitional)
- Wildflower Seed (Native mixes, regional collections)
- California Collection (CA-native species)
- Clover Seed (lawn alternatives, cover crops)
- Food Plot Seed (deer, wildlife)
- Cover Crop Seed (soil health)
- Planting Aids (mulch, fertilizer)

Website: naturesseed.com
"""

ARTICLE_SYSTEM_PROMPT = f"""You are an expert SEO content writer for Nature's Seed,
a premium seed company at naturesseed.com.

{BRAND_CONTEXT}

When writing articles:
1. STRUCTURE: Use clear H2/H3 hierarchy. Start with a compelling intro that addresses
   the reader's intent. Include a brief answer in the first paragraph (for featured snippets).
2. SEO: Naturally incorporate the target keyword in H1, first paragraph, at least 2 H2s,
   and throughout the body. Aim for 1-2% keyword density.
3. INTERNAL LINKS: Reference Nature's Seed products where relevant using markdown links
   to naturesseed.com product pages. Format: [Product Name](https://naturesseed.com/products/category/slug/)
4. IMAGES: Insert image placeholders as: [IMAGE: descriptive alt text here] — these will
   be matched to WordPress media library images.
5. E-E-A-T: Demonstrate expertise with specific data, species names, planting rates,
   zone information. Cite practical experience.
6. LENGTH: 1,500-2,500 words for comprehensive guides.
7. CTA: End with a natural call-to-action mentioning relevant Nature's Seed products.
8. SCHEMA: Include FAQ section at the end (3-5 questions) for FAQ schema markup.

Output Format:
Return a JSON object with these fields:
- "title": SEO-optimized H1 title (50-60 characters ideal)
- "meta_description": Meta description (150-160 characters)
- "slug": URL-friendly slug
- "content": Full article HTML with proper heading tags, paragraphs, lists, etc.
- "primary_keyword": The main keyword targeted
- "secondary_keywords": Array of related keywords used
- "internal_links": Array of {{url, anchor_text}} objects for products mentioned
- "image_suggestions": Array of {{alt_text, context}} objects for where images should go
- "faq": Array of {{question, answer}} objects for FAQ schema
"""


def generate_article_draft(topic, keywords=None, vertical=None,
                           products=None, custom_instructions=None):
    """Generate an SEO article draft using Claude API."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_prompt = f"Write a comprehensive SEO article about: {topic}\n\n"

    if keywords:
        user_prompt += f"Target keywords: {', '.join(keywords)}\n"
    if vertical:
        user_prompt += f"Product vertical: {vertical}\n"
    if products:
        user_prompt += f"Relevant Nature's Seed products to mention:\n"
        for p in products[:8]:
            user_prompt += f"  - {p['name']} (/{p.get('slug', '')}/) — {p.get('short_description', '')[:100]}\n"
    if custom_instructions:
        user_prompt += f"\nAdditional instructions: {custom_instructions}\n"

    user_prompt += "\nReturn the article as a JSON object with the fields specified in your system prompt."

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Parse the JSON from Claude's response
    text = response.content[0].text
    # Handle case where Claude wraps in ```json blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        article = json.loads(text)
    except json.JSONDecodeError:
        # If JSON parsing fails, return raw text as content
        article = {
            "title": topic.title(),
            "meta_description": f"Learn about {topic} with Nature's Seed expert guide.",
            "slug": topic.lower().replace(" ", "-")[:60],
            "content": text,
            "primary_keyword": topic,
            "secondary_keywords": keywords or [],
            "internal_links": [],
            "image_suggestions": [],
            "faq": [],
        }

    return article


def refine_article(article_content, feedback):
    """Refine an existing article draft based on editor feedback."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Here is an article draft:\n\n{article_content}"},
            {"role": "assistant", "content": "I see the article draft. What changes would you like?"},
            {"role": "user", "content": f"Please make these changes and return the updated JSON:\n{feedback}"},
        ],
    )

    text = response.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"content": text, "error": "Could not parse refined article as JSON"}


def generate_outline(topic, keywords=None):
    """Generate just an article outline before full draft."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Create a detailed article outline for: {topic}

Target keywords: {', '.join(keywords) if keywords else topic}

Return JSON with:
- "title": Proposed H1
- "meta_description": Proposed meta description
- "sections": Array of {{"heading": "H2 text", "subheadings": ["H3 text", ...], "key_points": ["point", ...]}}
- "word_count_target": Recommended word count
- "products_to_mention": Which Nature's Seed products fit naturally
- "image_needs": What images would enhance the article
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"outline": text}
