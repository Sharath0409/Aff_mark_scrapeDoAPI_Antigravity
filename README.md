# Autonomous Affiliate Blog Generation Pipeline
**System Architecture & Engineering Blueprint**

## 1. Architecture Overview
This system is designed as a fully autonomous, highly fault-tolerant ETL (Extract, Transform, Load) pipeline tailored for AI-driven affiliate marketing. The architecture separates concerns into discrete, modular components to ensure scalability, ease of maintenance, and robust error handling.

**Data Flow:**
1. **Extraction**: The system reads pending blog topics and keywords from a Google Sheet. It then queries Amazon via the **Scrape.do API** (utilizing proxy rotation and anti-bot bypassing) to extract top-ranking products, prices, ratings, and features.
2. **Transformation**: The scraped raw data is injected into optimized Prompt Templates. The **Deepseek API** synthesizes this into a cohesive, SEO-optimized, human-sounding blog post complete with HTML formatting, comparison tables, pros/cons, and Amazon Associate links.
3. **Loading**: The finished HTML payload is pushed to **Blogger.com** via its REST API. The Google Sheet is then updated with the live URL or an error stack trace.
4. **Orchestration**: The entire pipeline is orchestrated via a **GitHub Actions** cron job, operating entirely serverless. An SMTP notifier acts as a watchdog, alerting the user when the topic queue is running low.

---

## 2. Complete Project Structure

```text
autoblogger/
├── .github/
│   └── workflows/
│       └── daily_publisher.yml       # GitHub Actions cron job definition
├── config/
│   ├── settings.py                   # Centralized configuration (loads .env / secrets)
│   └── logger.py                     # Custom logger setup (stream & file handlers)
├── core/
│   ├── sheets_manager.py             # Google Sheets API interactions (read/write)
│   ├── scraper.py                    # Amazon scraping logic using Scrape.do
│   ├── content_generator.py          # Deepseek API integration & prompt engineering
│   ├── blogger_publisher.py          # Blogger API v3 integration (publish/draft)
│   └── notifier.py                   # Email warning system (SMTP)
├── templates/
│   └── prompts.py                    # Jinja2 / string templates for Deepseek
├── utils/
│   ├── retry.py                      # Exponential backoff decorators (@retry)
│   ├── text_cleaner.py               # HTML sanitization, JSON extraction
│   └── affiliate.py                  # Affiliate tag injection logic
├── main.py                           # Application entry point and workflow orchestrator
├── requirements.txt                  # Python dependencies
├── .env.example                      # Template for local environment variables
└── README.md                         # Developer documentation (this file)
```

### File Purposes:
- `settings.py`: Validates that all required environment variables are present before execution starts.
- `sheets_manager.py`: Connects via Google Service Account to fetch `Pending` rows and write back `Success`/`Failed`.
- `scraper.py`: Handles HTTP requests to Scrape.do, parses BeautifulSoup elements, handles pagination and empty results.
- `content_generator.py`: Manages the token limits, system messages, and JSON-structured outputs from Deepseek.
- `blogger_publisher.py`: Handles Google OAuth2 refresh tokens and pushes the final HTML payload to Blogger.
- `prompts.py`: Stores the system prompts to ensure consistent tone, SEO structure, and formatting.

---

## 3. Inputs Required from User

To deploy this system, the user must provide the following credentials and configurations. Locally, these go in a `.env` file; in production, they go into **GitHub Actions Secrets**.

| Secret Name | Description / Source | Example Format |
| :--- | :--- | :--- |
| `DEEPSEEK_API_KEY` | Deepseek dashboard -> API Keys. | `sk-...` |
| `SCRAPE_DO_TOKEN` | Scrape.do dashboard API token. | `9a8b7c6d5e4f...` |
| `AMAZON_AFFILIATE_TAG` | Your Amazon Associates Store ID. | `myblog-20` |
| `GOOGLE_SHEET_ID` | The alphanumeric ID in your Google Sheet URL. | `1BxiMVs0XRY...` |
| `GCP_SERVICE_ACCOUNT` | Base64 encoded JSON key for Google Cloud Service Account (for Sheets API). | `eyJwcm9qZWN...` |
| `BLOGGER_BLOG_ID` | The ID of your Blogger site (found in Blogger URL). | `1234567890...` |
| `BLOGGER_CLIENT_ID` | GCP OAuth 2.0 Client ID. | `...apps.googleusercontent.com` |
| `BLOGGER_CLIENT_SECRET` | GCP OAuth 2.0 Client Secret. | `GOCSPX-...` |
| `BLOGGER_REFRESH_TOKEN`| OAuth2 Refresh token generated locally via consent screen. | `1//0g...` |
| `SMTP_EMAIL` | Sender Gmail address. | `mybot@gmail.com` |
| `SMTP_APP_PASSWORD` | 16-character Gmail App Password (2FA required). | `abcd efgh ijkl mnop` |

---

## 4. Google Sheet Structure

Create a Google Sheet and share it with your Service Account email (Editor permissions).

| Topic | Keyword | Category | Search Intent | Status | Publish Date | Blog URL | Error Log |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Best Gaming Mice | gaming mouse | Tech | Transactional | Pending | | | |
| Top Ergonomic Chairs | ergonomic office chair | Home | Transactional | Success | 2024-05-10 | `https://...` | |
| Mechanical Keyboards | mechanical keyboard | Tech | Informational | Failed | 2024-05-11 | | Timeout |

**Validation Rules:**
- **Status Column**: Must use Data Validation dropdown: `Pending`, `Success`, `Failed`.
- The system will ONLY process the first row from the top where `Status == 'Pending'`.

---

## 5. Scraping Requirements & Strategy

**The Scrape.do Advantage**: Scrape.do handles residential proxy rotation and headless browser rendering to bypass Amazon's aggressive anti-bot protections.

**Scraping Strategy:**
1. **Search Query**: Construct Amazon search URL: `https://www.amazon.com/s?k={keyword}`.
2. **Fetch via Scrape.do**: Send the request to `api.scrape.do?token=XXX&url=ENCODED_URL`. Use the `geo=us` parameter to ensure USD pricing.
3. **Parse Products**: Extract the top 3 to 5 organic product ASINs, avoiding sponsored posts.
4. **Product Details**: For each ASIN, hit the product page to extract:
   - Title
   - Price (handling missing prices gracefully)
   - Rating & Review Count
   - Main Image URL
   - Bullet point features
5. **Fallback Logic**: If the page structure changes, rely on generic CSS selectors (`[data-component-type="s-search-result"]`) or use a fallback secondary proxy provider.
6. **Anti-block Handling**: Implement a randomized delay (`time.sleep(uniform(2, 5))`) between Scrape.do calls, even though the API handles IP rotation, to prevent triggering rate limits on the Scrape.do account.

---

## 6. AI Content Generation Requirements

**Workflow:**
111:We utilize Deepseek's `deepseek-v4-flash` for high-quality reasoning and HTML generation.

**Chunking Strategy (To prevent Hallucinations & Timeouts):**
Instead of generating the whole blog in one API call, chunk it:
1. **Call 1 (Outline & Intro)**: Generate SEO Title, Meta Description, and engaging intro.
2. **Call 2 (Product Reviews)**: Feed the scraped JSON data. Prompt the AI to write 300 words per product, highlighting pros/cons based on extracted features.
3. **Call 3 (Buying Guide & FAQ)**: Generate generic buying advice and FAQ Schema markup.
4. **Assembly**: Python concatenates the chunks, injecting HTML and the affiliate links (`https://amazon.com/dp/{ASIN}?tag={AFFILIATE_TAG}`).

**Prompt Engineering for SEO:**
- "Act as an expert product reviewer. Use a conversational, authoritative tone."
- "Avoid AI buzzwords like 'In conclusion', 'Delve into', 'Tapestry'."
- "Structure the output in pure HTML5."
- "Include a comparison table using HTML `<table>` tags."

---

## 7. Blogger Publishing Workflow

**Authentication Flow:**
Because Blogger creates posts on behalf of a user, Service Accounts often face permission issues. We use standard **OAuth 2.0 with a Refresh Token**.
1. Run a local script once to log in via browser and generate a `refresh_token`.
2. Store `refresh_token` in GitHub Secrets.
3. The script uses the `google-auth` library to mint a fresh, short-lived `access_token` automatically on every run.

**Publishing:**
- Construct the JSON payload for Blogger API `posts.insert`:
  ```json
  {
    "kind": "blogger#post",
    "title": "Generated SEO Title",
    "content": "Full HTML String including images and affiliate links",
    "labels": ["Category from Sheet", "Review"]
  }
  ```
- Send POST request. On success, extract `url` and update Google Sheets.

---

## 8. GitHub Actions Automation

Create `.github/workflows/daily_publisher.yml`:

```yaml
name: Autonomous Affiliate Publisher

on:
  schedule:
    - cron: '0 12 * * *' # Runs every day at 12:00 PM UTC
  workflow_dispatch: # Allows manual trigger from GitHub UI

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Dependencies
        run: pip install -r requirements.txt

      - name: Run Publisher Pipeline
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          SCRAPE_DO_TOKEN: ${{ secrets.SCRAPE_DO_TOKEN }}
          AMAZON_AFFILIATE_TAG: ${{ secrets.AMAZON_AFFILIATE_TAG }}
          GCP_SERVICE_ACCOUNT: ${{ secrets.GCP_SERVICE_ACCOUNT }}
          BLOGGER_BLOG_ID: ${{ secrets.BLOGGER_BLOG_ID }}
          BLOGGER_CLIENT_ID: ${{ secrets.BLOGGER_CLIENT_ID }}
          BLOGGER_CLIENT_SECRET: ${{ secrets.BLOGGER_CLIENT_SECRET }}
          BLOGGER_REFRESH_TOKEN: ${{ secrets.BLOGGER_REFRESH_TOKEN }}
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          SMTP_EMAIL: ${{ secrets.SMTP_EMAIL }}
          SMTP_APP_PASSWORD: ${{ secrets.SMTP_APP_PASSWORD }}
        run: python main.py
```

---

## 9. Error Handling & Retry Architecture

Use the `tenacity` library in Python for robust exponential backoff.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_amazon_page(url):
    # Scrape.do call
    pass
```

**Failure Scenarios:**
- **Empty Product Results**: If scraper finds 0 products, abort run, mark sheet as `Failed: No products found`.
- **Deepseek Timeout**: Retries up to 3 times. If fails, marks sheet `Failed: Deepseek Error`.
- **API Limits**: Rate limits return HTTP 429. Tenacity catches this, waits (4s, 8s, 10s), and retries.
- **Malformed HTML**: BeautifulSoup `find()` fails. Handled via `try-except` blocks logging errors.

---

## 10. Email Warning System

In `main.py`, after fetching the sheet:
1. Calculate `pending_count = len(rows.where(Status == 'Pending'))`.
2. If `pending_count <= 5`, invoke `notifier.py`.
3. Connects to `smtp.gmail.com` on port 587 using TLS.
4. Sends an email: *"ALERT: Autoblogger is running out of topics. Only {pending_count} left. Please update the Google Sheet."*

---

## 11. Cost Optimization & Analytics

**Estimates per Post:**
- **Scrape.do**: ~5 API calls per post. Cost is negligible (starts at $30/mo for 250k credits).
- **Deepseek API**: ~3000 input tokens, ~2000 output tokens via `deepseek-v4-flash`. Approx cost will depend on Deepseek pricing.
- **Hosting**: $0 (GitHub Actions free tier covers this entirely).
- **Total Cost per month** (30 posts): estimate based on Deepseek pricing plus Scrape.do costs.

**Optimization:**
- Use `deepseek-v4-flash` for the Intro/Conclusion and the comparison matrix.
- Cache scraped products locally in a small SQLite DB if you plan to reuse the same ASINs across different articles.
- Token reduction: truncate massive product descriptions and reviews before feeding them to Deepseek.

---

## 12. SEO & Schema Strategy
- **NLP Headings**: H1 contains main keyword. H2s contain LSI (Latent Semantic Indexing) keywords (e.g., "Is [Product] worth it?").
- **Comparison Tables**: Google’s Helpful Content Update loves tables. Deepseek is prompted to output `<table class="comparison">` summarizing features.
- **Pros & Cons**: Explicit `<ul>` lists for Pros and Cons (crucial for affiliate SEO).
- **Schema**: Embed this JSON-LD at the bottom of the HTML:
  ```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [...]
  }
  </script>
  ```
- **Internal Linking**: Fetch previous entries from the Blogger API or Sheets and inject links Contextually via the LLM.

---

## 13. Scaling Recommendations & Future Improvements
- **Scale**: Once generating revenue, duplicate the repository for different niches, changing only the Sheet ID and prompts.
- **Future Additions**: 
  - Add an image generator using Deepseek image generation to create a custom featured image.
  - Implement a programmatic YouTube search to embed a relevant video, increasing page dwell time.
  - Track clicks by appending UTM parameters to the Amazon Affiliate links and using an analytics API.

## 14. Deployment Checklist
1. All API keys obtained and verified.
2. Google Sheet formatted and populated with at least 10 seed topics.
3. Service Account added as Editor to Google Sheet.
4. Blogger OAuth Refresh Token generated and tested locally.
5. GitHub Repository created.
6. GitHub Secrets populated (`DEEPSEEK_API_KEY`, `SCRAPE_DO_TOKEN`, `GCP_SERVICE_ACCOUNT`, `BLOGGER_REFRESH_TOKEN`, `SMTP_APP_PASSWORD`, etc.).
7. `.github/workflows/daily_publisher.yml` committed.
8. Dry-run executed successfully from the Actions tab.

## 15. Monitoring Strategy
- Monitor execution logs in the GitHub Actions dashboard.
- Set GitHub Actions to send email alerts on workflow failure.
- Rely on the integrated Google Sheets `Error Log` column to debug data-level or API-level failures transparently.