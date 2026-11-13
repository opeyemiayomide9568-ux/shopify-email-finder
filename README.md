# Shopify Email Finder

A local starter app for finding business email addresses that stores publicly display on a small set of pages.

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run `python -m venv .venv`
4. Activate the environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
5. Run `pip install -r requirements.txt`
6. Run `python app.py`
7. Open `http://127.0.0.1:5000`

## Scope and safeguards
- Up to 25 URLs per scan.
- Checks homepage, common contact/about pages, and contact-information policy page.
- Checks `robots.txt` before each page and skips pages if permission cannot be confirmed.
- One store at a time with a delay between stores.
- Only extracts email addresses visible in page text, mailto links, and visible accessibility/title attributes.
- Does not log in, bypass access controls, inspect private accounts, or guarantee exhaustive discovery.

Before deploying publicly, add authentication, request quotas, abuse monitoring, HTTPS, secure hosting configuration, and a clear privacy notice. Follow applicable privacy and anti-spam laws and respect opt-outs.
