"""
fetch_intel.py — SAS Competitive Intelligence Feed
Fetches RSS feeds, analyzes with Claude, saves JSON, and optionally emails a digest.

Usage:
    python fetch_intel.py              # full run
    python fetch_intel.py --dry-run    # fetch feeds only, skip Claude + email
    python fetch_intel.py --hours 168  # extend lookback to 7 days
    python fetch_intel.py --file path/to/report.pdf  # attach a context document
"""

import argparse
import json
import os
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote_plus

import anthropic
import feedparser
from dotenv import load_dotenv

from config import COMPETITORS, FEED_USER_AGENT, SYSTEM_PROMPT

load_dotenv()

FEED_FILE = "intel_feed.json"
LOOKBACK_HOURS = 80  # slightly over 72h to avoid boundary misses
MAX_ITEMS_PER_FEED = 8
MAX_ITEMS_PER_COMPETITOR = 15


# ── RSS FETCHING ──────────────────────────────────────────────────────────────

def google_news_url(query: str) -> str:
    return (
        f"https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )


def fetch_feed(url: str, cutoff: datetime) -> list[dict]:
    """Fetch a single RSS feed and return items newer than cutoff."""
    items = []
    try:
        feed = feedparser.parse(url, agent=FEED_USER_AGENT)
        http_status = getattr(feed, "status", 0)

        if http_status in (403, 404, 410):
            print(f"      ↳ HTTP {http_status}: {url[:65]}")
            return []

        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue

            title = entry.get("title", "").strip()
            summary = (entry.get("summary", "") or "")[:600].strip()
            if not title:
                continue

            items.append({
                "title": title,
                "summary": summary,
                "link": entry.get("link", ""),
                "published": entry.get("published", "unknown date"),
            })
    except Exception as e:
        print(f"      ↳ Feed error: {e}")

    return items


def fetch_competitor_items(competitor: dict, hours: int = LOOKBACK_HOURS) -> list[dict]:
    """Fetch all feeds for a competitor, deduplicated."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_items = []

    # 1. Direct / newsroom feeds
    for url in competitor.get("feeds", []):
        items = fetch_feed(url, cutoff)
        if items:
            print(f"      ✓ {len(items)} item(s) from {url[:60]}")
        all_items.extend(items)
        time.sleep(0.3)

    # 2. Google News fallback (always run — catches trade press)
    for query in competitor.get("google_news_queries", []):
        url = google_news_url(query)
        items = fetch_feed(url, cutoff)
        if items:
            print(f"      ✓ {len(items)} item(s) via Google News: '{query}'")
        all_items.extend(items)
        time.sleep(0.3)

    # Deduplicate by normalized title
    seen, deduped = set(), []
    for item in all_items:
        key = item["title"].lower()[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:MAX_ITEMS_PER_COMPETITOR]


# ── CLAUDE ANALYSIS ───────────────────────────────────────────────────────────

def build_analysis_prompt(all_items: dict[str, list], context_files: list[str] = None) -> str:
    lines = ["Recent RSS feed items collected from SAS Intelligent Decisioning competitors:\n"]

    for comp_name, items in all_items.items():
        lines.append(f"## {comp_name}")
        if not items:
            lines.append("No recent articles found in this scan window.\n")
            continue
        for item in items:
            lines.append(f"- **{item['title']}** ({item['published']})")
            if item["summary"]:
                lines.append(f"  {item['summary'][:400]}")
        lines.append("")

    if context_files:
        lines.append("\n## Additional Context Documents Provided\n")
        for path in context_files:
            lines.append(f"- {path} (attached below)")

    lines.append("\nReturn only the JSON analysis. No preamble.")
    return "\n".join(lines)


def run_claude_analysis(all_items: dict[str, list], context_files: list[str] = None) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = build_analysis_prompt(all_items, context_files)

    # Build message content — text first, then any attached documents
    content = [{"type": "text", "text": prompt}]

    if context_files:
        import base64
        for path in context_files:
            try:
                with open(path, "rb") as f:
                    data = base64.standard_b64encode(f.read()).decode("utf-8")
                ext = path.rsplit(".", 1)[-1].lower()
                media_type = {
                    "pdf": "application/pdf",
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                }.get(ext, "application/octet-stream")
                content.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": media_type, "data": data},
                })
                print(f"  Attached context file: {path}")
            except Exception as e:
                print(f"  Warning: Could not attach {path}: {e}")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start : end + 1])
        raise ValueError(f"Could not parse JSON from Claude response:\n{raw[:500]}")


# ── OUTPUT ────────────────────────────────────────────────────────────────────

def save_json(data: dict, path: str = FEED_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved → {path}")


def build_email_html(data: dict) -> str:
    generated = data.get("generated_at", "")
    sections = []

    # Market signals
    signals = data.get("market_signals", [])
    if signals:
        bullets = "".join(f"<li style='margin-bottom:6px'>{s}</li>" for s in signals)
        sections.append(
            f"<h2 style='color:#1e40af'>📡 Market Signals</h2>"
            f"<ul style='padding-left:20px'>{bullets}</ul>"
        )

    # Competitors sorted by threat
    threat_order = {"high": 0, "medium": 1, "low": 2}
    competitors = sorted(
        data.get("competitors", []),
        key=lambda c: threat_order.get(c.get("threat_level", "low"), 2),
    )

    threat_labels = {"high": "🔴 HIGH", "medium": "🟡 MEDIUM", "low": "🟢 LOW"}
    rows = ""
    for c in competitors:
        label = threat_labels.get(c.get("threat_level", "low"), "🟢 LOW")
        rows += (
            f"<tr>"
            f"<td style='padding:10px;border:1px solid #e2e8f0;vertical-align:top'>"
            f"<strong>{c['name']}</strong><br>"
            f"<span style='color:#6b7280;font-size:12px'>{c.get('strategic_posture','')}</span></td>"
            f"<td style='padding:10px;border:1px solid #e2e8f0;vertical-align:top'>{c.get('headline','—')}</td>"
            f"<td style='padding:10px;border:1px solid #e2e8f0;text-align:center;white-space:nowrap'>{label}</td>"
            f"</tr>"
        )
    sections.append(
        f"<h2 style='color:#1e40af'>Competitor Snapshot</h2>"
        f"<table style='width:100%;border-collapse:collapse;font-size:13px'>"
        f"<thead><tr style='background:#f8fafc'>"
        f"<th style='padding:10px;border:1px solid #e2e8f0;text-align:left'>Competitor</th>"
        f"<th style='padding:10px;border:1px solid #e2e8f0;text-align:left'>Latest Development</th>"
        f"<th style='padding:10px;border:1px solid #e2e8f0'>Threat</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )

    # Recommendations
    recs = data.get("recommendations", [])
    if recs:
        pri_colors = {"critical": "#dc2626", "high": "#d97706", "medium": "#2563eb"}
        rec_html = ""
        for r in recs:
            color = pri_colors.get(r.get("priority", "medium"), "#2563eb")
            rec_html += (
                f"<li style='margin-bottom:14px'>"
                f"<span style='color:{color};font-weight:bold'>[{r.get('priority','').upper()}]</span> "
                f"<strong>{r.get('area','')}</strong><br>"
                f"<span style='font-size:13px'>{r.get('action','')}</span><br>"
                f"<em style='color:#6b7280;font-size:12px'>{r.get('rationale','')}</em>"
                f"</li>"
            )
        sections.append(
            f"<h2 style='color:#1e40af'>Strategic Recommendations</h2>"
            f"<ol style='padding-left:20px'>{rec_html}</ol>"
        )

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;max-width:780px;margin:0 auto;padding:28px;color:#1e293b">
<h1 style="color:#1e40af;margin-bottom:4px">SAS Intelligent Decisioning</h1>
<h2 style="font-weight:normal;color:#64748b;margin-top:0">Competitive Intelligence Digest</h2>
<p style="color:#94a3b8;font-size:12px;border-bottom:1px solid #e2e8f0;padding-bottom:16px">
  Generated: {generated}
</p>
{body}
<hr style="border:none;border-top:1px solid #e2e8f0;margin:28px 0">
<p style="font-size:11px;color:#94a3b8">
  SAS Intel Feed &middot; Runs Mon &amp; Thu &middot; Powered by Claude &middot;
  <a href="https://github.com" style="color:#94a3b8">View in GitHub</a>
</p>
</body></html>"""


def send_email(data: dict) -> None:
    from_addr = os.getenv("EMAIL_FROM")
    to_addr = os.getenv("EMAIL_TO")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not all([from_addr, to_addr, password]):
        print("⚠  Email env vars not set (EMAIL_FROM / EMAIL_TO / EMAIL_PASSWORD). Skipping.")
        return

    html = build_email_html(data)
    date_str = datetime.now().strftime("%b %d, %Y")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SAS Competitive Intel — {date_str}"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            smtp.login(from_addr, password)
            smtp.sendmail(from_addr, to_addr, msg.as_string())
        print(f"✓ Email sent → {to_addr}")
    except Exception as e:
        print(f"✗ Email failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SAS Intel Feed")
    parser.add_argument("--dry-run", action="store_true", help="Fetch feeds only; skip Claude + email")
    parser.add_argument("--hours", type=int, default=LOOKBACK_HOURS, help="Lookback window in hours")
    parser.add_argument("--file", nargs="*", metavar="PATH", help="PDF/image files to include as context")
    args = parser.parse_args()

    print(f"\nSAS Intel Feed  —  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Lookback: {args.hours}h  |  Competitors: {len(COMPETITORS)}\n")

    # 1. Fetch RSS feeds
    all_items: dict[str, list] = {}
    for comp in COMPETITORS:
        print(f"  {comp['name']}")
        items = fetch_competitor_items(comp, hours=args.hours)
        all_items[comp["name"]] = items
        print(f"    → {len(items)} unique item(s) total\n")

    total = sum(len(v) for v in all_items.values())
    print(f"Total items collected: {total}")

    if args.dry_run:
        print("\n[dry-run] Skipping Claude analysis and email.")
        return

    # 2. Claude analysis
    print("\nRunning Claude analysis...")
    data = run_claude_analysis(all_items, context_files=args.file)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()

    # 3. Save JSON
    save_json(data)

    # 4. Email
    send_email(data)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
