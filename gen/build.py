#!/usr/bin/env python3
"""Build the Callbassador preview site from gen/src plus page and blog sources.

gen/src is the current production snapshot (unpacked site bundle). This script
copies it, applies the preview changes, and writes _bundle/site.tgz.b64 so a
later run of gen/build.py reproduces the same site. It does not deploy.

The in-page Retell web call is wired in gen/src (#cb-voice-modal, data-talk-sami,
?talk=1). TALK_TO_SAMI_ENABLED stays True because of that. Set it False to render
a disabled placeholder instead of opening the modal.
"""
from __future__ import annotations

import base64
import hashlib
import html
import io
import os
import re
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(__file__).resolve().parent / "src"
PARTIALS = Path(__file__).resolve().parent / "partials"
PAGES = Path(__file__).resolve().parent / "pages"
POSTS = Path(__file__).resolve().parent / "posts"
CSS_FILE = Path(__file__).resolve().parent / "preview.css"

# Retell voice modal is already in the baseline pages. Keep the button live.
TALK_TO_SAMI_ENABLED = True

SITE = "https://callbassador.com"
PRO_URL = "https://buy.stripe.com/8x27sL6zme2C3aS19n1Jm02"
NOV_URL = "https://buy.stripe.com/00waEXbTG6AacLs05j1Jm01"
NOV_PLAN = "Pro — $99/mo (November Special · 400 min, 24/7)"
PRO_PLAN = "Pro — $149/mo (14-day free trial)"

SAMI_LAST_LINE = (
    "Perfect, that stops more water from coming in. I'm texting your address "
    "and number to our on-call tech right now, and he'll call you back with his ETA."
)

POST_ORDER = [
    "missed-calls-after-hours.html",
    "answering-service-vs-ai-receptionist-vs-office-manager.html",
    "forward-calls-to-ai-receptionist.html",
    "answering-service-cost.html",
]

PIXEL = """<!-- Meta Pixel Code --><script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init','2107351423234410');fbq('track','PageView');</script><noscript><img height="1" width="1" alt="" style="display:none" src="https://www.facebook.com/tr?id=2107351423234410&ev=PageView&noscript=1"/></noscript><!-- End Meta Pixel Code -->"""

RETELL = """<script id="retell-widget" src="https://dashboard.retellai.com/retell-widget-v2.js" type="module" data-public-key="public_key_a72c1c071b62a97efde23" data-agent-id="agent_91a86fc78b06f0d54aa6a615e5" data-title="Chat with Callbassador" data-bot-name="Sami (AI assistant)" data-color="#10275A" data-fab-text="Chat with Sami" data-logo-url="https://callbassador.com/assets/mark-c.png" data-white-label="rT_1c6e4d9g8i0a5b3f2j7h_kL"></script>"""

TOGGLE = """<script id="cb-nav-toggle">(function(){var b=document.querySelector('.nav-toggle');var u=document.getElementById('site-nav');if(!b||!u)return;b.addEventListener('click',function(){var open=u.classList.toggle('is-open');b.setAttribute('aria-expanded',open?'true':'false');});})();</script>"""


def make_hero_card_html(extra_class: str = "") -> str:
    """Example call card used in the hero and on trade pages."""
    classes = "phone hero-card" + (f" {extra_class}" if extra_class else "")
    last = SAMI_LAST_LINE
    return f"""<!--hero-card-start--><div class="{classes}" id="hero-card" aria-label="Example call transcript">
<div class="tag">Example &middot; Sami, an AI receptionist &middot; 2:14 AM</div>
<div class="b s">Thanks for calling Miller Plumbing &amp; Heating, this is Sami! How can I help you today?</div>
<div class="b">Hey, yeah&mdash;our water heater just started leaking all over the basement floor.<span class="hide-mobile"> Do you guys have anyone who can come out today?</span></div>
<div class="b s">Oh no, I'll get this to our on-call tech. What's the street address, and is the shut-off valve reachable?</div>
<div class="b hide-mobile">It's 412 Oak Lane in West Chester, and yeah, I just turned the top valve off.</div>
<div class="b s hide-mobile">{last}</div>
<div class="tag">&#10003; Emergency and address texted to the owner</div>
</div><!--hero-card-end-->"""


def talk_markup(surface: str, loc: str) -> str:
    btn = "btn ghost" if surface == "dark" else "btn line"
    if TALK_TO_SAMI_ENABLED:
        return (
            f'<div class="talk-wrap"><a class="{btn}" href="#talk-to-sami" data-talk-sami="1" '
            f'data-cta-loc="{loc}">Talk to Sami, our AI receptionist</a>'
            f'<span class="talk-sub">Uses your mic, about 2 minutes</span></div>'
        )
    return (
        f'<div class="talk-wrap"><button type="button" class="{btn}" disabled>'
        f'Talk to Sami, our AI receptionist</button>'
        f'<span class="talk-sub">Uses your mic, about 2 minutes. The in-page voice demo is off in this build.</span></div>'
    )


def prefix_for(rel: str) -> str:
    return "../" * rel.count("/")


def make_nav(prefix: str, on_home: bool) -> str:
    trial = "#signup" if on_home else f"{prefix}index.html#signup"
    items = [
        ("how-it-works.html", "How it works"),
        ("pricing.html", "Pricing"),
        ("faq.html", "FAQ"),
        ("about.html", "About"),
        ("security.html", "Security"),
        ("blog/", "Blog"),
    ]
    lis = "".join(f'<li><a href="{prefix}{href}">{label}</a></li>' for href, label in items)
    return (
        '<button type="button" class="nav-toggle" aria-expanded="false" aria-controls="site-nav">Menu</button>'
        f'<nav aria-label="Main"><ul id="site-nav">{lis}</ul>'
        f'<a class="btn sm" href="{trial}" data-cta-loc="nav">Start 14-day free trial</a></nav>'
    )


def make_footer(prefix: str) -> str:
    p = prefix
    return f"""<footer><div class="wrap fcols">
<div><img src="{p}assets/logo-full-reversed.png" alt="Callbassador" width="551" height="104"><p>Catch every call. Catch every job.<br>Home-service businesses in all 50 states.<br>Callbassador LLC, a Pennsylvania LLC<br>64 E Uwchlan Ave, Suite 241, Exton, PA 19341<br><a href="mailto:hello@callbassador.com">hello@callbassador.com</a></p><p>Sami is an AI receptionist.</p></div>
<div><h2>Trades</h2><ul>
<li><a href="{p}answering-service/">All trades and areas</a></li>
<li><a href="{p}answering-service/plumbers-philadelphia.html">Plumbers in Philadelphia</a></li>
<li><a href="{p}answering-service/hvac-philadelphia.html">HVAC in Philadelphia</a></li>
<li><a href="{p}answering-service/cleaning-companies.html">Cleaning companies</a></li>
</ul></div>
<div><h2>Product</h2><ul>
<li><a href="{p}how-it-works.html">How it works</a></li>
<li><a href="{p}pricing.html">Pricing</a></li>
<li><a href="{p}faq.html">FAQ</a></li>
<li><a href="{p}blog/">Blog</a></li>
</ul></div>
<div><h2>Company</h2><ul>
<li><a href="{p}about.html">About</a></li>
<li><a href="{p}security.html">Security</a></li>
<li><a href="{p}index.html#refer">Refer a contractor</a></li>
<li><a href="mailto:hello@callbassador.com">Email</a></li>
</ul></div>
<div><h2>Legal</h2><ul>
<li><a href="{p}privacy.html">Privacy Policy</a></li>
<li><a href="{p}terms.html">Terms</a></li>
</ul><p>© 2026 Callbassador LLC</p></div>
</div><p class="chatnote">Chats with Sami on this site are saved so we can reply and improve the service. See our <a href="{p}privacy.html">Privacy Policy</a>.</p></footer>"""


def ensure_chrome(page: str, rel: str) -> str:
    prefix = prefix_for(rel)
    nav = make_nav(prefix, rel == "index.html")
    if re.search(r'<nav aria-label="Main">', page):
        page = re.sub(r'<nav aria-label="Main">.*?</nav>', nav, page, count=1, flags=re.S)
        if 'class="nav-toggle"' not in page:
            page = page.replace(nav, nav, 1)
    else:
        page = page.replace("</div></header>", nav + "</div></header>", 1)
    # Drop a duplicate toggle if a previous nav already included one and the header had one.
    while page.count('class="nav-toggle"') > 1:
        page = page.replace(
            '<button type="button" class="nav-toggle" aria-expanded="false" aria-controls="site-nav">Menu</button>',
            "",
            1,
        )
    foot = make_footer(prefix)
    if "<footer>" in page:
        page = re.sub(r"<footer>.*?</footer>", foot, page, count=1, flags=re.S)
    else:
        page = re.sub(
            r'(<script src="(?:\.\./)?assets/cb-analytics\.js")',
            foot + r"\1",
            page,
            count=1,
        )
    if "cb-nav-toggle" not in page:
        page = page.replace("</body>", TOGGLE + "</body>", 1)
    trial = "#signup" if rel == "index.html" else f"{prefix}index.html#signup"
    page = page.replace(
        'href="#demo" data-cb-trial="1"',
        f'href="{trial}" data-cb-trial="1"',
    )
    page = page.replace(
        'href="index.html#demo" data-cb-trial="1"',
        f'href="{trial}" data-cb-trial="1"',
    )
    return page


def strip_special(page: str) -> str:
    """Remove the November plan from pages other than pricing."""
    page = re.sub(r"<option[^>]*November Special[^>]*>.*?</option>\s*", "", page, flags=re.S)
    page = page.replace(f'value="{NOV_PLAN}"', f'value="{PRO_PLAN}"')
    page = page.replace(
        "Pro ($99/mo after 14-day free trial · $0 today)",
        "Pro ($149/mo after 14-day free trial · $0 today)",
    )
    page = page.replace(
        "Pro ($99/mo after 14-day free trial &middot; $0 today)",
        "Pro ($149/mo after 14-day free trial &middot; $0 today)",
    )
    page = page.replace(
        "Pro — $99/mo for 12 months (14-day free trial)",
        "Pro — $149/mo (14-day free trial)",
    )
    page = page.replace(
        '<input type="hidden" name="_next" value="https://buy.stripe.com/00waEXbTG6AacLs05j1Jm01">',
        f'<input type="hidden" name="_next" value="{PRO_URL}">',
    )
    page = page.replace(
        'href="https://buy.stripe.com/00waEXbTG6AacLs05j1Jm01"',
        f'href="{PRO_URL}"',
    )
    page = page.replace(
        "else base='https://buy.stripe.com/00waEXbTG6AacLs05j1Jm01';",
        f"else base='{PRO_URL}';",
    )
    page = page.replace(
        "||'Pro — $99/mo (November Special · 400 min, 24/7)'",
        f"||'{PRO_PLAN}'",
    )
    page = page.replace(
        "Promotional pricing (for example, $99/mo on Pro) stays the same for 12 months from the start date.",
        "When a promotional monthly rate is offered on the pricing page, that rate stays the same for 12 months from the start date.",
    )
    return page


def patch_index(page: str) -> str:
    old_card = """<div class="phone hero-card rv-card" aria-label="Example call transcript">
<div class="tag">Incoming call &middot; 2:14 AM</div>
<div class="b s">Thanks for calling Liberty Plumbing, this is Sami. How can I help you today?</div>
<div class="b">My basement's flooding, a pipe burst!</div>
<div class="b s">I'm flagging this as an emergency and texting the on-call tech right now. What's the address?</div>
<div class="tag">&#10003; Emergency texted to owner</div>
</div>"""
    if old_card not in page:
        raise SystemExit("homepage hero card block not found")
    page = page.replace(old_card, make_hero_card_html("rv-card"), 1)
    old_cta = """<div class="rv-cta">
<a class="btn" href="#demo" data-cta-loc="hero_trial">Start 14-day free trial</a>
</div>"""
    new_cta = (
        '<div class="rv-cta">\n<a class="btn" href="#signup" data-cta-loc="hero_trial">Start 14-day free trial</a>\n'
        + talk_markup("dark", "hero_talk")
        + "\n</div>"
    )
    if old_cta not in page:
        raise SystemExit("homepage hero CTA not found")
    page = page.replace(old_cta, new_cta, 1)
    under = (PARTIALS / "under_hero.html").read_text(encoding="utf-8")
    under = under.replace("__TALK_LIGHT__", talk_markup("light", "steps_talk"))
    wizard = (PARTIALS / "wizard.js").read_text(encoding="utf-8")
    under = under.replace('<script src="__WIZARD_JS__"></script>', "<script>\n" + wizard + "\n</script>")
    marker = "<section><div class=\"wrap\">\n<h2>A missed call is often a job for the next guy on Google.</h2>"
    if marker not in page:
        raise SystemExit("missed-call section not found")
    page = page.replace(marker, under + "\n" + marker, 1)
    page = re.sub(r"<!--demo-sec-start-->.*?<!--demo-sec-end-->", "", page, count=1, flags=re.S)
    page = page.replace(
        "The plumber will get your details right away and call you back.",
        "The plumber will get your details and call you back.",
    )
    page = page.replace("Wants callback ASAP.", "Asked for a callback.")
    page = page.replace('href="#demo" data-cta-loc="final_trial"', 'href="#signup" data-cta-loc="final_trial"')
    return page


def parse_fragment(text: str) -> tuple[dict, str]:
    m = re.match(r"<!--\s*(.*?)\s*-->\s*(.*)\Z", text, re.S)
    if not m:
        raise SystemExit("fragment missing metadata comment")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip()
    return meta, m.group(2).strip()


def word_count(fragment: str) -> int:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = re.sub(r"&[a-z#0-9]+;", " ", text, flags=re.I)
    return len(text.split())


def json_ld(obj: dict) -> str:
    import json
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"


def shell(rel: str, title: str, description: str, canonical: str, body: str, kind: str, extra_ld: str = "") -> str:
    prefix = prefix_for(rel)
    modal = MODAL
    trial = f"{prefix}index.html#signup"
    modal = modal.replace('href="#demo" data-cb-trial="1"', f'href="{trial}" data-cb-trial="1"')
    og_type = "article" if kind == "article" else "website"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{html.escape(canonical)}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{html.escape(canonical)}">
<meta property="og:image" content="{SITE}/assets/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#10275A">
<link rel="icon" href="{prefix}favicon.ico">
<link rel="apple-touch-icon" href="{prefix}assets/apple-touch-icon.png">
<link rel="stylesheet" href="{prefix}styles.css">
{extra_ld}
{RETELL}
<meta name="google-site-verification" content="92gxx1w5qIXZvOTAhNHDHLDitZpcf46zaI1guJYBl18" />
{PIXEL}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header><div class="wrap nav">
<a href="{prefix}index.html" aria-label="Callbassador home"><img src="{prefix}assets/logo-full-no-tagline.png" alt="Callbassador" width="556" height="92"></a>
{make_nav(prefix, False)}
</div></header>
<main id="main"><div class="wrap prose" style="padding:48px 20px 72px">
{body}
</div></main>
{make_footer(prefix)}
<script src="{prefix}assets/cb-analytics.js" defer></script>
{TOGGLE}
{modal}
</body>
</html>
"""


def article_ld(meta: dict, canonical: str) -> str:
    return json_ld({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta["title"],
        "description": meta["description"],
        "datePublished": meta["date"],
        "dateModified": meta["date"],
        "author": {"@type": "Organization", "name": "Callbassador Team"},
        "publisher": {
            "@type": "Organization",
            "name": "Callbassador LLC",
            "url": SITE,
            "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/mark-c.png"},
        },
        "mainEntityOfPage": canonical,
        "image": f"{SITE}/assets/og-image.png",
    })


def render_posts(dist: Path) -> list[dict]:
    metas = []
    blog = dist / "blog"
    blog.mkdir(parents=True, exist_ok=True)
    for name in POST_ORDER:
        meta, body = parse_fragment((POSTS / name).read_text(encoding="utf-8"))
        count = word_count(body)
        print(f"post {name}: {count} words")
        if not 800 <= count <= 1200:
            raise SystemExit(f"{name} word count {count} is outside 800-1200")
        canonical = meta["canonical"]
        slug = name
        rel = f"blog/{slug}"
        inner = (
            f'<p class="byline">Callbassador Team · {html.escape(meta["date"])}</p>\n'
            f'<h1>{html.escape(meta["title"])}</h1>\n'
            f'{body}\n'
            f'<p><a href="./">All posts</a> · <a href="../index.html#signup">Start 14-day free trial</a></p>'
        )
        page = shell(
            rel,
            meta.get("seo_title") or meta["title"],
            meta["description"],
            canonical,
            inner,
            "article",
            article_ld(meta, canonical),
        )
        (blog / slug).write_text(page, encoding="utf-8")
        metas.append(meta | {"file": slug, "words": count})
    cards = []
    for meta in metas:
        cards.append(
            f'<a href="{html.escape(meta["file"])}"><h2>{html.escape(meta["title"])}</h2>'
            f'<p>{html.escape(meta["description"])}</p></a>'
        )
    index_body = (
        "<h1>Blog</h1>\n"
        "<p>Practical notes for home-service owners: missed calls, what answering coverage costs, and how to keep the number you already use. Sami is an AI receptionist. Callbassador LLC serves home-service businesses in all 50 states.</p>\n"
        f'<div class="post-list">{"".join(cards)}</div>'
    )
    index_ld = json_ld({
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "Callbassador Blog",
        "url": f"{SITE}/blog/",
        "publisher": {"@type": "Organization", "name": "Callbassador LLC"},
    })
    (blog / "index.html").write_text(
        shell(
            "blog/index.html",
            "Blog | Callbassador",
            "Guides for home-service owners on missed calls, answering-service cost, and forwarding to an AI receptionist.",
            f"{SITE}/blog/",
            index_body,
            "website",
            index_ld,
        ),
        encoding="utf-8",
    )
    return metas


def render_pages(dist: Path) -> None:
    for path in sorted(PAGES.glob("*.html")):
        meta, body = parse_fragment(path.read_text(encoding="utf-8"))
        rel = path.name
        page = shell(rel, meta["title"], meta["description"], meta["canonical"], body, "website")
        (dist / rel).write_text(page, encoding="utf-8")


def update_sitemap(dist: Path) -> None:
    text = (dist / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>(.*?)</loc>", text)
    extra = [
        f"{SITE}/about.html",
        f"{SITE}/how-it-works.html",
        f"{SITE}/pricing.html",
        f"{SITE}/faq.html",
        f"{SITE}/security.html",
        f"{SITE}/blog/",
    ] + [f"{SITE}/blog/{name}" for name in POST_ORDER]
    seen = []
    for loc in locs + extra:
        if loc not in seen:
            seen.append(loc)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc in seen:
        lines.append(f"<url><loc>{loc}</loc><lastmod>2026-11-09</lastmod></url>")
    lines.append("</urlset>\n")
    (dist / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")


def update_llms(dist: Path) -> None:
    path = dist / "llms.txt"
    text = path.read_text(encoding="utf-8")
    extra = """
## Site pages
- About: https://callbassador.com/about.html
- How it works: https://callbassador.com/how-it-works.html
- Pricing: https://callbassador.com/pricing.html
- FAQ: https://callbassador.com/faq.html
- Security and recording: https://callbassador.com/security.html
- Blog: https://callbassador.com/blog/
"""
    if "## Site pages" not in text:
        path.write_text(text.rstrip() + "\n" + extra, encoding="utf-8")


def visible(page: str) -> str:
    page = re.sub(r"<script\b[^>]*>.*?</script>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<style\b[^>]*>.*?</style>", " ", page, flags=re.S | re.I)
    return page


def scan(dist: Path) -> None:
    problems = []
    banned = [
        "under five minutes",
        "within 5 minutes",
        "within five minutes",
        "in 3 seconds",
        "Call Sami",
        "Ramshield",
        "Founding",
        "founding",
        "22-second",
        "22 seconds",
        "22-Sec",
        "tel:",
    ]
    for path in dist.rglob("*.html"):
        raw = path.read_text(encoding="utf-8", errors="replace")
        vis = visible(raw)
        rel = str(path.relative_to(dist))
        for phrase in banned:
            if phrase in vis or (phrase == "tel:" and "tel:" in raw):
                if phrase == "tel:" and "tel:" not in raw:
                    continue
                if phrase == "tel:" and "tel:" in raw:
                    problems.append(f"{rel}: contains tel:")
                    continue
                if phrase in vis:
                    problems.append(f"{rel}: contains {phrase!r}")
        if "cb-sticky-cta" in raw and "cb-sticky-cta" in vis:
            problems.append(f"{rel}: sticky bar markup")
        if rel not in ("pricing.html",) and "November Special" in vis:
            # Homepage may show it only inside the pricing section.
            if rel == "index.html":
                outside = re.sub(r'<section class="alt" id="pricing">.*?</section>', " ", vis, flags=re.S)
                if "November Special" in outside or "$99" in outside:
                    problems.append("index.html: $99 or November Special outside the pricing section")
            elif "$99" in vis or "November Special" in vis:
                # Competitor price pages may cite PATLive's $99 plan. That is not our special.
                if "PATLive" in vis and "November Special" not in vis:
                    pass
                else:
                    problems.append(f"{rel}: promotional price outside pricing")
        if rel != "pricing.html" and rel != "index.html" and "November Special" in vis:
            problems.append(f"{rel}: November Special visible")
    hero = (dist / "index.html").read_text(encoding="utf-8")
    if SAMI_LAST_LINE not in hero:
        problems.append("homepage missing corrected Sami line")
    if problems:
        raise SystemExit("copy scan failed:\n" + "\n".join(problems))


def pack(dist: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for dirpath, dirnames, filenames in os.walk(dist):
            dirnames.sort()
            for fn in sorted(filenames):
                full = Path(dirpath) / fn
                rel = full.relative_to(dist).as_posix()
                tar.add(full, arcname="./" + rel)
    target = ROOT / "_bundle" / "site.tgz.b64"
    target.write_bytes(base64.b64encode(buf.getvalue()))


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SRC.is_dir():
        raise SystemExit("gen/src baseline is missing")
    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    shutil.copytree(SRC, dist)
    global MODAL
    modal_text = (SRC / "index.html").read_text(encoding="utf-8")
    m = re.search(r"<!--voice-modal-start-->.*?<!--voice-modal-end-->", modal_text, re.S)
    if not m:
        raise SystemExit("voice modal block missing from baseline")
    MODAL = m.group(0)

    css = (dist / "styles.css").read_text(encoding="utf-8")
    extra = CSS_FILE.read_text(encoding="utf-8")
    if "preview-ia-start" not in css:
        (dist / "styles.css").write_text(css + "\n" + extra, encoding="utf-8")

    index_path = dist / "index.html"
    index_path.write_text(patch_index(index_path.read_text(encoding="utf-8")), encoding="utf-8")

    for path in dist.rglob("*.html"):
        rel = path.relative_to(dist).as_posix()
        text = path.read_text(encoding="utf-8")
        if rel != "index.html" and "<!--hero-card-start-->" in text:
            text = re.sub(
                r"<!--hero-card-start-->.*?<!--hero-card-end-->",
                make_hero_card_html(),
                text,
                count=1,
                flags=re.S,
            )
        text = text.replace("Wants callback ASAP.", "Asked for a callback.")
        text = text.replace(
            "The plumber will get your details right away and call you back.",
            "The plumber will get your details and call you back.",
        )
        if rel not in ("index.html",):
            text = strip_special(text)
        else:
            text = text.replace(
                "Promotional pricing (for example, $99/mo on Pro) stays the same for 12 months from the start date.",
                "When a promotional monthly rate is offered on the pricing page, that rate stays the same for 12 months from the start date.",
            )
        text = ensure_chrome(text, rel)
        path.write_text(text, encoding="utf-8")

    render_pages(dist)
    render_posts(dist)
    update_sitemap(dist)
    update_llms(dist)
    scan(dist)

    for name in ("sami-sample-call.mp3", "sample-call.mp3"):
        a = hash_file(SRC / "assets" / name)
        b = hash_file(dist / "assets" / name)
        if a != b:
            raise SystemExit(f"audio file changed: {name}")

    pack(dist)
    for name in ("index.html", "styles.css", "terms.html"):
        shutil.copy(dist / name, ROOT / name)
    print("built", dist)
    print("talk to Sami enabled:", TALK_TO_SAMI_ENABLED)


if __name__ == "__main__":
    main()
