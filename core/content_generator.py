from openai import OpenAI
from config.logger import get_logger
from config import settings
from templates.prompts import SYSTEM_PROMPT, INTRO_TEMPLATE, REVIEW_TEMPLATE

logger = get_logger(__name__)

class ContentGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
    def generate_section(self, prompt, model="gpt-4o"):
        """Call OpenAI API to generate content."""
        logger.info(f"Generating content with model {model}")
        # Mocked API call for safety during scaffolding
        # response = self.client.chat.completions.create(
        #     model=model,
        #     messages=[
        #         {"role": "system", "content": SYSTEM_PROMPT},
        #         {"role": "user", "content": prompt}
        #     ]
        # )
        # return response.choices[0].message.content
        return f"<p>Mocked AI generated content for prompt...</p>"
        
    def generate_full_post(self, topic, keyword, products):
        """Assemble the complete blog post."""
        logger.info("Starting full post generation")
        
        intro_prompt = INTRO_TEMPLATE.format(topic=topic, keyword=keyword)
        intro_html = self.generate_section(intro_prompt, model="gpt-4o-mini")
        
        reviews_html = ""
        for p in products:
            r_prompt = REVIEW_TEMPLATE.format(
                title=p['title'], price=p['price'], 
                rating=p['rating'], review_count=p['review_count'], 
                features=p['features']
            )
            reviews_html += self.generate_section(r_prompt, model="gpt-4o")
            
        full_html = f"<h1>{topic}</h1>\n{intro_html}\n{reviews_html}"
        return full_html
