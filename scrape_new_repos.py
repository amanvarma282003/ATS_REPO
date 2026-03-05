"""
Scraper for 4 new repos added to refer/:
  1. 450-free-courses   -> HTML format (classcentral links) -> source: ivy-league-courses
  2. Free-Certifications -> Markdown table format           -> source: free-certifications
  3. Free-Courses        -> Simple bullet list              -> source: free-courses-extras
  4. Developer-Resources-Hub -> Markdown * [title](url)    -> source: developer-resources-hub

Merges into candidates/fixtures/learning_resources.json (deduplicates by url+source).
"""

import re
import json
import os
import html as html_module

BASE = "/home/akhil/Downloads/temp/ATS_Major"
REFER = os.path.join(BASE, "refer")
FIXTURE = os.path.join(BASE, "candidates", "fixtures", "learning_resources.json")

# ------------------------------------------------------------------
# Category normalization map (extend existing one)
# ------------------------------------------------------------------
CATEGORY_MAP = {
    # existing normalizations
    "math": "Mathematics",
    "maths": "Mathematics",
    "mathematics": "Mathematics",
    "angularjs": "Angular",
    "angular js": "Angular",
    "angular": "Angular",
    "mongodb": "MongoDB",
    "mongo db": "MongoDB",
    "php": "PHP",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "vue.js": "Vue.js",
    "real time systems": "Real-Time Systems",
    "real-time systems": "Real-Time Systems",
    "systems programming": "Systems Programming",
    "full stack web development": "Full Stack Web Development",
    "fullstack": "Full Stack Web Development",
    "full stack": "Full Stack Web Development",
    "web programming": "Web Programming and Internet Technologies",
    "web programming and internet technologies": "Web Programming and Internet Technologies",
    "computer science": "Introduction to Computer Science",
    "intro to cs": "Introduction to Computer Science",
    "introduction to computer science": "Introduction to Computer Science",
    "data structures": "Data Structures and Algorithms",
    "data structures and algorithms": "Data Structures and Algorithms",
    "algorithms": "Data Structures and Algorithms",
    "artificial intelligence": "Artificial Intelligence",
    "ai": "Artificial Intelligence",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "computer networks": "Computer Networks",
    "networking": "Computer Networks",
    "network": "Computer Networks",
    "security": "Security",
    "cybersecurity": "Security",
    "cyber security": "Security",
    "blockchain": "Blockchain Development",
    "blockchain development": "Blockchain Development",
    "database": "Database Systems",
    "databases": "Database Systems",
    "database systems": "Database Systems",
    "python": "Python",
    "java": "Java",
    "javascript": "Web Programming and Internet Technologies",
    "go": "Go",
    "golang": "Go",
    "ruby": "Ruby",
    "swift": "Swift",
    "android": "Android",
    "react": "React",
    "docker": "Docker",
    "devops": "Tools",
    "tools": "Tools",
    "programming": "Programming",
    "general": "General",
    "misc": "Misc",
    "miscellaneous": "Misc",
    "data science": "Machine Learning",
    "data analytics": "Machine Learning",
    "computer architecture": "Computer Organization and Architecture",
    "computer organization and architecture": "Computer Organization and Architecture",
    "software engineering": "Software Engineering",
    "embedded systems": "Embedded Systems",
    "robotics": "Robotics and Control",
    "robotics and control": "Robotics and Control",
    "image processing": "Image Processing and Computer Vision",
    "image processing and computer vision": "Image Processing and Computer Vision",
    "computer vision": "Image Processing and Computer Vision",
    "computer graphics": "Computer Graphics",
    "theoretical cs": "Theoretical CS and Programming Languages",
    "theoretical cs and programming languages": "Theoretical CS and Programming Languages",
    "quantum computing": "Quantum Computing",
    "computational biology": "Computational Biology",
    "computational finance": "Computational Finance",
    "computational physics": "Computational Physics",
    "network science": "Network Science",
    "bash": "Bash",
    "shell": "Bash",
    "applications": "Applications",
    # new from 450-free-courses
    "humanities": "General",
    "business": "General",
    "art & design": "General",
    "art design": "General",
    "science": "General",
    "social sciences": "General",
    "health & medicine": "General",
    "health medicine": "General",
    "engineering": "General",
    "education & teaching": "General",
    "education teaching": "General",
    "personal development": "General",
    # new from Free-Certifications
    "project management": "General",
    "marketing": "General",
    "cloud": "Tools",
    "cloud computing": "Tools",
    # new from Developer-Resources-Hub
    "ai / ml / ds resources": "Machine Learning",
    "ai / ml / ds reference links": "Machine Learning",
    "github repositories": "General",
    "free courses": "General",
    "books & references": "General",
    "books references": "General",
    "aptitude & logical reasoning": "General",
    "aptitude logical reasoning": "General",
    "custom gpts": "Artificial Intelligence",
    "custom gpthttps": "Artificial Intelligence",
    "graphic designing": "General",
    "coding questions": "Data Structures and Algorithms",
    "notes and to-do lists": "General",
    "notes and todo lists": "General",
    "useful links": "General",
    "app links": "Applications",
    "css formatter": "Web Programming and Internet Technologies",
    "mariadb": "Database Systems",
    "mysql": "Database Systems",
    "postgresql": "Database Systems",
    "sql": "Database Systems",
    "nosql": "Database Systems",
    "iot": "Embedded Systems",
    "internet of things": "Embedded Systems",
    "frontend": "Web Programming and Internet Technologies",
    "backend": "Full Stack Web Development",
    "notebooklm": "Tools",
    "ai art tools": "Artificial Intelligence",
    "courses": "General",
    "online presence": "General",
    "blogging platforms": "General",
    "recommended apps": "General",
    "notes and to-do lists": "General",
    "databases": "Database Systems",
    "general links": "General",
    "programming languages": "Programming",
    "ds resources": "Machine Learning",
    "mlops & machine learning journeys": "Machine Learning",
    "mlops machine learning journeys": "Machine Learning",
    "beginner-friendly articles": "General",
    "books & learning resources": "General",
    "books learning resources": "General",
    "cheatsheets & quick references": "General",
    "cheatsheets quick references": "General",
    "dev apps": "Applications",
    "project link": "General",
    "project links": "General",
    "project repositories": "General",
    "repositories & notes": "General",
    "repositories notes": "General",
    "interactive notebooks": "Tools",
    "study resources": "General",
    "utility": "Tools",
    "video courses": "General",
    "website links": "General",
    "website resources": "General",
    "pdf guides": "General",
    "pdf tools": "Tools",
    "learning & community updates": "General",
    "learning community updates": "General",
    "selling projects & digital products": "General",
    "selling projects digital products": "General",
    "art & design": "General",
    "art design": "General",
    "health & medicine": "General",
    "health medicine": "General",
    "education & teaching": "General",
    "education teaching": "General",
    "social sciences": "General",
    "humanities": "General",
    "business": "General",
    "science": "General",
    "personal development": "General",
    "engineering": "General",
}


def normalize_category(raw: str) -> str:
    # decode HTML entities (e.g. &amp; -> &)
    raw = html_module.unescape(raw)
    # strip markdown bold/italic/code markers
    raw = re.sub(r'[*_`]+', '', raw).strip()
    # filter out numbered list headers like "2. Using Tool..."
    if re.match(r'^\d+[\.\)]\s+', raw):
        return "General"
    # filter out empty or too-long strings
    if not raw or len(raw) > 80:
        return "General"
    key = raw.strip().lower()
    # strip special chars for lookup
    key_clean = re.sub(r"[^\w\s&/]", "", key).strip()
    # normalize ampersand variants
    key_clean = key_clean.replace("&amp;", "&")
    if key_clean in CATEGORY_MAP:
        return CATEGORY_MAP[key_clean]
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]
    # title-case fallback
    return raw.strip().title() if raw.strip() else "General"


# ------------------------------------------------------------------
# 1. 450-free-courses  (HTML format)
# ------------------------------------------------------------------
def scrape_450_free_courses():
    path = os.path.join(REFER, "450-free-courses", "README.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    records = []
    current_category = "General"

    # find <h2 ...> tags for category and <li><a href="...">title</a> for links
    lines = content.splitlines()
    for line in lines:
        # detect h2 section
        h2_match = re.search(r'<h2[^>]*><strong>(.*?)</strong></h2>', line, re.IGNORECASE)
        if h2_match:
            raw_cat = re.sub(r'\s*\(\d+\)', '', h2_match.group(1)).strip()
            raw_cat = html_module.unescape(raw_cat)
            current_category = normalize_category(raw_cat)
            continue

        # detect anchor links (skip TOC hrefs starting with #)
        link_match = re.search(r'<a href="(https?://[^"]+)"[^>]*>(.*?)</a>', line, re.IGNORECASE)
        if link_match:
            url = link_match.group(1).strip()
            title = re.sub(r'<[^>]+>', '', link_match.group(2)).strip()
            # strip utm params for cleaner URLs
            url_clean = re.sub(r'\?utm_source.*', '', url)
            if title and url_clean:
                records.append({
                    "title": title,
                    "url": url_clean,
                    "category": current_category,
                    "source": "ivy-league-courses",
                })

    return records


# ------------------------------------------------------------------
# 2. Free-Certifications (Markdown table format)
# ------------------------------------------------------------------
def scrape_free_certifications():
    path = os.path.join(REFER, "Free-Certifications", "README.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    records = []
    current_category = "General"

    for line in content.splitlines():
        # detect ## section header
        h2_match = re.match(r'^##\s+(.+)', line)
        if h2_match:
            current_category = normalize_category(h2_match.group(1).strip())
            continue

        # detect table row: | ... | ... | ... | [Link](url) | ...
        # Skip separator rows (|---|---|)
        if not line.startswith('|') or re.match(r'^\|\s*[-:]+\s*\|', line):
            continue

        # extract all [Link](url) style patterns
        url_matches = re.findall(r'\[(?:Link|link|here|Click)\]\((https?://[^)]+)\)', line, re.IGNORECASE)
        if not url_matches:
            # try any markdown link in the row
            url_matches = re.findall(r'\]\((https?://[^)]+)\)', line)

        if not url_matches:
            continue

        # extract title from first column (| Technology | ...)
        cols = [c.strip() for c in line.split('|') if c.strip()]
        title = cols[0] if cols else "Resource"
        # strip markdown formatting from title
        title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', title)
        title = re.sub(r'[*_`]', '', title).strip()

        # get provider from second column if available
        provider = cols[1] if len(cols) > 1 else ""
        provider = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', provider)
        provider = re.sub(r'[*_`]', '', provider).strip()

        if title and title.lower() in ("technology", "link", "course"):
            continue  # skip header rows

        full_title = f"{title} – {provider}" if provider and provider.lower() not in ("provider", "") else title

        for url in url_matches:
            records.append({
                "title": full_title,
                "url": url.strip(),
                "category": current_category,
                "source": "free-certifications",
            })

    return records


# ------------------------------------------------------------------
# 3. Free-Courses (simple bullet list)
# ------------------------------------------------------------------
def scrape_free_courses_extras():
    path = os.path.join(REFER, "Free-Courses", "README.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    records = []
    current_category = "General"

    for line in content.splitlines():
        h2_match = re.match(r'^##\s+(.+)', line)
        if h2_match:
            current_category = normalize_category(h2_match.group(1).strip())
            continue

        # - [title](url) or * [title](url)
        link_match = re.match(r'^[-*]\s+\[([^\]]+)\]\((https?://[^)]+)\)', line)
        if link_match:
            title = link_match.group(1).strip()
            url = link_match.group(2).strip()
            records.append({
                "title": title,
                "url": url,
                "category": current_category,
                "source": "free-courses-extras",
            })

    return records


# ------------------------------------------------------------------
# 4. Developer-Resources-Hub (Markdown * [title](url) format)
# ------------------------------------------------------------------
def scrape_developer_resources_hub():
    path = os.path.join(REFER, "Developer-Resources-Hub", "README.md")
    with open(path, encoding="utf-8") as f:
        content = f.read()

    records = []
    current_category = "General"

    for line in content.splitlines():
        # detect ## or ### headers
        h_match = re.match(r'^#{2,3}\s+(.+)', line)
        if h_match:
            raw = h_match.group(1).strip()
            # strip emoji prefix characters
            raw = re.sub(r'^[\U00010000-\U0010ffff\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\uFE0F\u20E3]+\s*', '', raw).strip()
            raw = re.sub(r'^[\uFE0F\u20E3\s]+', '', raw).strip()
            # strip markdown icon/badge refs
            raw = re.sub(r'!\[.*?\]\(.*?\)', '', raw).strip()
            current_category = normalize_category(raw)
            continue

        # * [title](url) – description
        link_match = re.search(r'\*?\s*\[([^\]]+)\]\((https?://[^)]+)\)', line)
        if link_match:
            title = link_match.group(1).strip()
            url = link_match.group(2).strip()
            # skip local file links and image urls
            if any(url.endswith(ext) for ext in ('.pdf', '.png', '.jpg', '.gif', '.svg', '.jpeg', '.webp')):
                continue
            if 'shields.io' in url or 'img.shields' in url:
                continue
            records.append({
                "title": title,
                "url": url,
                "category": current_category,
                "source": "developer-resources-hub",
            })

    return records


# ------------------------------------------------------------------
# Merge & deduplicate
# ------------------------------------------------------------------
def main():
    print("Loading existing fixture...")
    with open(FIXTURE, encoding="utf-8") as f:
        existing = json.load(f)

    existing_keys = set((r["url"], r["source"]) for r in existing)
    print(f"  Existing records: {len(existing)}")

    new_records = []
    new_records.extend(scrape_450_free_courses())
    new_records.extend(scrape_free_certifications())
    new_records.extend(scrape_free_courses_extras())
    new_records.extend(scrape_developer_resources_hub())

    print(f"  Scraped total (before dedup): {len(new_records)}")

    added = 0
    url_seen = set()
    for r in new_records:
        key = (r["url"], r["source"])
        if key in existing_keys:
            continue
        if r["url"] in url_seen:
            continue
        if not r["title"] or not r["url"]:
            continue
        url_seen.add(r["url"])
        existing.append(r)
        existing_keys.add(key)
        added += 1

    print(f"  New unique records added: {added}")
    print(f"  Total records after merge: {len(existing)}")

    with open(FIXTURE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print("Fixture saved.")

    # print breakdown by source
    from collections import Counter
    sources = Counter(r["source"] for r in existing)
    for src, cnt in sorted(sources.items()):
        print(f"    {src}: {cnt}")


if __name__ == "__main__":
    main()
