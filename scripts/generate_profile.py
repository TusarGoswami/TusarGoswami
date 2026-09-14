#!/usr/bin/env python3
"""Generate a dynamic SVG profile card for TusarGoswami's GitHub README.

Fetches live GitHub stats via REST + GraphQL APIs, calculates age dynamically,
and produces an SVG that closely reproduces the existing dark_mode.png design.

Runs via GitHub Actions on an hourly schedule. Uses only Python standard library.
"""

import os, sys, json, base64, re
import urllib.request, urllib.error
from datetime import date
from pathlib import Path
from calendar import monthrange
from xml.sax.saxutils import escape

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION — edit static profile info here
# ═══════════════════════════════════════════════════════════════════════

GITHUB_USERNAME = "TusarGoswami"
DOB = date(2004, 5, 7)

PROFILE = {
    "os": "Windows 11 Pro",
    "university": "Lovely Professional University",
    "course": "B.Tech Computer Science & Engineering",
    "passout": "July 2027",
    "ide": "VS Code 1.96.0",
    "lang_prog": "Java, Python, JavaScript, TypeScript, C++",
    "lang_web": "HTML, CSS, JSON, LaTeX, YAML",
    "lang_spoken": "English, Hindi, Bengali",
    "frontend": "React.js, Redux, Tailwind CSS, Three.js, Flutter",
    "backend": "Node.js, Express.js, Flask, Socket.IO",
    "database": "MongoDB, MySQL, SQLite",
    "tools": "Git, AWS (EC2), Vercel, Postman, Figma, Judge0 API",
    "projects": "Head-2-Code, Jarvis, Cosmic Voyage",
    "focus": "Full Stack Development, DSA, AI, Real-time Apps",
    "learning": "System Design, Scalable Architectures, AI Agents",
    "interests": "Coding, 3D Web, Automation, Gaming, Traveling",
    "email": "tusargoswami0027@gmail.com",
    "linkedin": "linkedin.com/in/tusar027",
    "github": f"github.com/{GITHUB_USERNAME}",
}

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets" / "profile.svg"
PORTRAIT = ROOT / "assets" / "portrait.png"

# ═══════════════════════════════════════════════════════════════════════
# COLORS & LAYOUT — matched from dark_mode.png
# ═══════════════════════════════════════════════════════════════════════

BG       = "#0d1117"
BORDER   = "#30363d"
GREEN    = "#3fb950"
YELLOW   = "#e8a735"
VALUE_C  = "#c9d1d9"
DOTS_C   = "#6e7681"
BLUE     = "#58a6ff"
FOOTER_BG = "#161b22"
FONT     = "'Consolas','Monaco','Courier New','Liberation Mono',monospace"

# SVG dimensions (proportional to 1536×1024 original)
W, H = 960, 640
RX   = 400        # right panel text x-start
FS   = 13         # font size
LH   = 21         # line height
PORTRAIT_W = 380  # portrait display width
PORTRAIT_H = 567  # portrait display height (from crop)

# ═══════════════════════════════════════════════════════════════════════
# GITHUB API HELPERS
# ═══════════════════════════════════════════════════════════════════════

TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api_get(endpoint: str):
    """GET from GitHub REST API. Returns (json_data, headers) or (None, None)."""
    url = f"https://api.github.com{endpoint}" if endpoint.startswith("/") else endpoint
    headers = {"Accept": "application/vnd.github.v3+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), resp.headers
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  [!] REST error for {url}: {e}", file=sys.stderr)
        return None, None


def api_graphql(query: str, variables: dict = None):
    """POST to GitHub GraphQL API. Returns data dict or None."""
    if not TOKEN:
        print(f"  [!] No GITHUB_TOKEN -- skipping GraphQL", file=sys.stderr)
        return None
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        if "errors" in result:
            print(f"  [!] GraphQL errors: {result['errors']}", file=sys.stderr)
        return result.get("data")
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  [!] GraphQL error: {e}", file=sys.stderr)
        return None


def next_page_url(headers) -> str | None:
    """Extract next page URL from GitHub Link header."""
    if not headers:
        return None
    link = headers.get("Link", "")
    for part in link.split(","):
        if 'rel="next"' in part:
            m = re.search(r"<(.+?)>", part)
            return m.group(1) if m else None
    return None


# ═══════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════


def fetch_user_stats() -> dict:
    """Fetch basic profile stats from REST API."""
    data, _ = api_get(f"/users/{GITHUB_USERNAME}")
    if not data:
        return {"repos": 0, "followers": 0, "following": 0}
    return {
        "repos": data.get("public_repos", 0),
        "followers": data.get("followers", 0),
        "following": data.get("following", 0),
    }


def fetch_total_stars() -> int:
    """Sum stargazers across all owned public repos (paginated)."""
    stars = 0
    url = f"/users/{GITHUB_USERNAME}/repos?per_page=100&type=owner"
    while url:
        data, headers = api_get(url)
        if not data:
            break
        stars += sum(r.get("stargazers_count", 0) for r in data)
        url = next_page_url(headers)
    return stars


def fetch_contributions() -> dict:
    """Fetch contribution stats via GraphQL.

    Returns:
        commits: total commit contributions in the last year (includes private)
        contributed: total repos contributed to (all time)
    """
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
        }
        repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE]) {
          totalCount
        }
      }
    }
    """
    data = api_graphql(query, {"username": GITHUB_USERNAME})
    if not data or not data.get("user"):
        return {"commits": 0, "contributed": 0}
    cc = data["user"]["contributionsCollection"]
    return {
        "commits": cc.get("totalCommitContributions", 0)
                   + cc.get("restrictedContributionsCount", 0),
        "contributed": data["user"].get("repositoriesContributedTo", {}).get("totalCount", 0),
    }


def fetch_loc_estimate() -> int:
    """Estimate total lines of code from GitHub language byte stats.

    Uses /repos/{owner}/{repo}/languages which returns bytes per language.
    Approximates LOC at ~45 bytes/line (typical for source code).
    Skips forked repos. This is an approximation, labeled with ≈ in the card.
    """
    repos = []
    url = f"/users/{GITHUB_USERNAME}/repos?per_page=100&type=owner"
    while url:
        data, headers = api_get(url)
        if not data:
            break
        repos.extend(r["full_name"] for r in data if not r.get("fork"))
        url = next_page_url(headers)

    total_bytes = 0
    for name in repos:
        data, _ = api_get(f"/repos/{name}/languages")
        if data:
            total_bytes += sum(data.values())
    return total_bytes // 45


def calculate_age() -> str:
    """Calculate age from DOB with proper date arithmetic."""
    today = date.today()
    years = today.year - DOB.year
    months = today.month - DOB.month
    days = today.day - DOB.day
    if days < 0:
        months -= 1
        prev_m = today.month - 1 or 12
        prev_y = today.year if today.month > 1 else today.year - 1
        days += monthrange(prev_y, prev_m)[1]
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def fetch_all_stats() -> dict:
    """Fetch all dynamic data. Returns a unified stats dict."""
    print("Fetching GitHub data...")
    user = fetch_user_stats()
    print(f"  [OK] User: {user['repos']} repos, {user['followers']} followers")

    stars = fetch_total_stars()
    print(f"  [OK] Stars: {stars}")

    contribs = fetch_contributions()
    print(f"  [OK] Commits: {contribs['commits']}, Contributed to: {contribs['contributed']}")

    loc = fetch_loc_estimate()
    print(f"  [OK] LOC estimate: ~{loc:,}")

    age = calculate_age()
    print(f"  [OK] Age: {age}")

    return {**user, "stars": stars, **contribs, "loc": loc, "age": age}


# ═══════════════════════════════════════════════════════════════════════
# SVG GENERATION
# ═══════════════════════════════════════════════════════════════════════


def fmt(n: int) -> str:
    """Format number with commas."""
    return f"{n:,}"


def load_portrait() -> str:
    """Load portrait as base64 data URI."""
    if not PORTRAIT.exists():
        print(f"  [!] Portrait not found: {PORTRAIT}", file=sys.stderr)
        return ""
    raw = PORTRAIT.read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def dotted(label: str, col: int = 20) -> str:
    """Create 'label ....... ' with dots padded to col width."""
    ndots = max(2, col - len(label))
    return f"{label} {'.' * ndots} "


def svg_text(x: int, y: int, parts: list[tuple[str, str]], size: int = FS) -> str:
    """Build a <text> element from a list of (color, content) tuples."""
    spans = "".join(f'<tspan fill="{c}">{escape(t)}</tspan>' for c, t in parts)
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}">{spans}</text>'


def generate_svg(stats: dict) -> str:
    """Build the complete SVG profile card string."""
    portrait_uri = load_portrait()

    lines = []
    a = lines.append  # shorthand

    # ── SVG root + clip path for rounded corners ──
    a(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
      f'viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    a(f'<defs><clipPath id="rc"><rect width="{W}" height="{H}" rx="10"/></clipPath></defs>')
    a(f'<g clip-path="url(#rc)">')

    # ── Background & border ──
    a(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    a(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="none" '
      f'stroke="{BORDER}" stroke-width="1"/>')

    # ── Portrait ──
    if portrait_uri:
        a(f'<image x="8" y="12" width="{PORTRAIT_W}" height="{PORTRAIT_H}" '
          f'href="{portrait_uri}" preserveAspectRatio="xMidYMid meet"/>')

    # ── Title bar ──
    dashes = "─" * 37
    a(svg_text(RX, 32, [(GREEN, "tusar@github"), (DOTS_C, f" {dashes}"), (DOTS_C, "[-]")], 15))
    a(f'<line x1="{RX}" y1="44" x2="{W-18}" y2="44" stroke="{BORDER}"/>')

    # ── Helper for info lines ──
    def info(y, icon, label, value, icon_c=BLUE, lbl_c=YELLOW, val_c=VALUE_C, col=20):
        parts = []
        if icon:
            parts.append((icon_c, icon + " "))
        parts.append((lbl_c, dotted(label, col)))
        parts.append((val_c, value))
        a(svg_text(RX, y, parts))

    def section_header(y, icon, title, icon_c=BLUE, title_c=YELLOW):
        a(svg_text(RX, y, [(icon_c, icon + " "), (title_c, title)]))

    y = 66

    # ── Section 1: System Info ──
    info(y, "⊞", "OS", PROFILE["os"]);                    y += LH
    info(y, "◷", "Age", stats["age"], val_c=GREEN);       y += LH
    info(y, "⊡", "University", PROFILE["university"]);    y += LH
    info(y, "⊟", "Course", PROFILE["course"]);            y += LH
    info(y, "◫", "Passout", PROFILE["passout"]);           y += LH
    info(y, "⊳", "IDE", PROFILE["ide"]);                   y += LH

    # ── Section 2: Languages ──
    y += 8
    info(y, "</>", "Languages.Programming", PROFILE["lang_prog"], col=24);  y += LH
    info(y, "",    "Languages.Web", PROFILE["lang_web"], col=24);           y += LH
    info(y, "",    "Languages.Spoken", PROFILE["lang_spoken"], col=24);     y += LH

    # ── Section 3: Tech Stack ──
    y += 8
    info(y, "⚙", "Frontend", PROFILE["frontend"]);    y += LH
    info(y, "",   "Backend", PROFILE["backend"]);       y += LH
    info(y, "",   "Database", PROFILE["database"]);     y += LH
    info(y, "",   "Tools", PROFILE["tools"]);           y += LH

    # ── Section 4: Projects & Focus ──
    y += 8
    info(y, "★", "Projects", PROFILE["projects"], icon_c=YELLOW);          y += LH
    info(y, "",   "Focus", PROFILE["focus"]);                               y += LH
    info(y, "",   "Currently Learning", PROFILE["learning"], col=22);       y += LH
    info(y, "",   "Interests", PROFILE["interests"]);                       y += LH

    # ── Section 5: Contact ──
    y += 8
    info(y, "✉", "Email", PROFILE["email"]);       y += LH
    info(y, "",   "LinkedIn", PROFILE["linkedin"]); y += LH
    info(y, "",   "GitHub", PROFILE["github"]);     y += LH

    # ── Section 6: GitHub Stats ──
    y += 8
    section_header(y, "⣿", "GitHub Stats")
    y += LH + 2

    # Stats grid: 3 columns
    c1, c2, c3 = RX, RX + 190, RX + 370
    a(svg_text(c1, y, [(YELLOW, dotted("Repos", 14)), (VALUE_C, fmt(stats["repos"]))]))
    a(svg_text(c2, y, [(YELLOW, dotted("Contributed", 14)), (VALUE_C, fmt(stats["contributed"]))]))
    a(svg_text(c3, y, [(YELLOW, dotted("Stars", 14)), (VALUE_C, fmt(stats["stars"]))]))
    y += LH
    a(svg_text(c1, y, [(YELLOW, dotted("Commits", 14)), (VALUE_C, fmt(stats["commits"]))]))
    a(svg_text(c2, y, [(YELLOW, dotted("Followers", 14)), (VALUE_C, fmt(stats["followers"]))]))
    a(svg_text(c3, y, [(YELLOW, dotted("Following", 14)), (VALUE_C, fmt(stats["following"]))]))
    y += LH
    loc_str = f"≈ {fmt(stats['loc'])}"
    a(svg_text(c1, y, [(YELLOW, dotted("Lines of Code", 16)), (VALUE_C, loc_str)]))
    y += LH

    # ── Footer bar ──
    fy = H - 48
    a(f'<rect x="0" y="{fy}" width="{W}" height="48" fill="{FOOTER_BG}"/>')
    a(f'<line x1="0" y1="{fy}" x2="{W}" y2="{fy}" stroke="{BORDER}"/>')
    a(svg_text(20, fy + 30, [
        (GREEN,  "tusar@github:~$"),
        (DOTS_C, "  |  "),
        (VALUE_C, '"Code. Build. Learn. Repeat."'),
        (DOTS_C, "  |  "),
        (YELLOW, '"Turning ideas into impactful products."'),
        (VALUE_C, " 🚀"),
    ]))

    # ── Close ──
    a("</g></svg>")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════


def main():
    stats = fetch_all_stats()
    svg = generate_svg(stats)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"\n[OK] SVG written to {OUTPUT} ({len(svg):,} bytes)")

    # Basic validation
    from xml.etree.ElementTree import fromstring
    try:
        fromstring(svg)
        print("[OK] SVG is valid XML")
    except Exception as e:
        print(f"[ERR] SVG XML validation failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Security check: ensure no tokens leaked
    if TOKEN and TOKEN in svg:
        print("[ERR] CRITICAL: Token found in SVG output!", file=sys.stderr)
        sys.exit(1)
    print("[OK] No tokens in SVG output")


if __name__ == "__main__":
    main()
