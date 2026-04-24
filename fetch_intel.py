"""
fetch_intel.py — SAS Competitive Intelligence Feed

Usage:
    python fetch_intel.py              # full run
    python fetch_intel.py --dry-run    # fetch feeds only, skip Claude + email
    python fetch_intel.py --hours 168  # extend lookback window
    python fetch_intel.py --file report.pdf  # attach context document
"""

import argparse
import base64
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
LOOKBACK_HOURS = 80
MAX_ITEMS_PER_FEED = 8
MAX_ITEMS_PER_COMPETITOR = 15

SOURCE_LABELS = {
    "blog":     "📝 Thought Leadership",
    "newsroom": "📣 Product / Company Update",
    "google":   "📰 Trade Press",
}

SOURCE_ICONS = {
    "blog":        ("📝", "Thought Leadership",   "#2563eb"),
    "newsroom":    ("📣", "Product / Co. Update", "#7c3aed"),
    "trade_press": ("📰", "Trade Press",          "#0891b2"),
}


# ── RSS FETCHING ──────────────────────────────────────────────────────────────

def google_news_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )


def fetch_feed(url: str, feed_type: str, cutoff: datetime) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url, agent=FEED_USER_AGENT)
        status = getattr(feed, "status", 0)
        if status in (403, 404, 410):
            print(f"      ↳ HTTP {status}: {url[:65]}")
            return []
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            title = (entry.get("title") or "").strip()
            if not title:
                continue
            items.append({
                "title": title,
                "summary": (entry.get("summary") or "")[:600].strip(),
                "link": entry.get("link", ""),
                "published": entry.get("published", "unknown date"),
                "source_type": feed_type,
            })
    except Exception as e:
        print(f"      ↳ Feed error: {e}")
    return items


def fetch_competitor_items(competitor: dict, hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_items = []

    for feed_cfg in competitor.get("feeds", []):
        items = fetch_feed(feed_cfg["url"], feed_cfg["type"], cutoff)
        if items:
            label = SOURCE_LABELS.get(feed_cfg["type"], feed_cfg["type"])
            print(f"      ✓ {len(items)} item(s) [{label}]")
        all_items.extend(items)
        time.sleep(0.3)

    for query in competitor.get("google_news_queries", []):
        items = fetch_feed(google_news_url(query), "google", cutoff)
        if items:
            print(f"      ✓ {len(items)} item(s) [📰 Trade Press] via: '{query}'")
        all_items.extend(items)
        time.sleep(0.3)

    seen, deduped = set(), []
    for item in all_items:
        key = item["title"].lower()[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:MAX_ITEMS_PER_COMPETITOR]


# ── CLAUDE ANALYSIS ───────────────────────────────────────────────────────────

def build_prompt(all_items: dict, context_files: list | None) -> str:
    lines = [
        "Recent RSS items from SAS Intelligent Decisioning competitors.",
        "Each item tagged: blog | newsroom | google\n",
    ]
    for comp_name, items in all_items.items():
        lines.append(f"## {comp_name}")
        if not items:
            lines.append("No recent articles found.\n")
            continue
        for item in items:
            lines.append(f"- [{item['source_type'].upper()}] {item['title']} ({item['published']})")
            if item["summary"]:
                lines.append(f"  {item['summary'][:350]}")
        lines.append("")
    if context_files:
        lines.append("\n## Additional Context Documents")
        for p in context_files:
            lines.append(f"- {p} (attached)")
    lines.append("\nReturn only the JSON. No preamble.")
    return "\n".join(lines)


def parse_json(raw: str) -> dict:
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise ValueError(f"Could not parse JSON from response:\n{raw[:400]}")


def run_claude_analysis(all_items: dict, context_files: list | None = None) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message_content = [{"type": "text", "text": build_prompt(all_items, context_files)}]

    if context_files:
        for path in (context_files or []):
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
                message_content.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": media_type, "data": data},
                })
                print(f"  Attached: {path}")
            except Exception as e:
                print(f"  Warning — could not attach {path}: {e}")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message_content}],
    )

    if response.stop_reason == "max_tokens":
        print("  ⚠ Response truncated — retrying in concise mode...")
        concise_text = build_prompt(all_items, context_files)
        concise_text += (
            "\n\nIMPORTANT: Be very concise. Max 1 development per competitor, "
            "1 sentence each. Return only the JSON."
        )
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": [{"type": "text", "text": concise_text}]}],
        )

    return parse_json(response.content[0].text)


# ── JSON OUTPUT ───────────────────────────────────────────────────────────────

def save_json(data: dict, path: str = FEED_FILE) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved → {path}")


# ── EMAIL ─────────────────────────────────────────────────────────────────────

def build_email_html(data: dict) -> str:
    generated = data.get("generated_at", "")
    sections = []

    signals = data.get("market_signals", [])
    if signals:
        bullets = "".join(f"<li style='margin-bottom:6px'>{s}</li>" for s in signals)
        sections.append(
            f"<h2 style='color:#1e40af'>📡 Market Signals</h2>"
            f"<ul style='padding-left:20px'>{bullets}</ul>"
        )

    threat_order = {"high": 0, "medium": 1, "low": 2}
    threat_labels = {"high": "🔴 HIGH", "medium": "🟡 MED", "low": "🟢 LOW"}
    competitors = sorted(
        data.get("competitors", []),
        key=lambda c: threat_order.get(c.get("threat_level", "low"), 2),
    )

    rows = ""
    for c in competitors:
        label = threat_labels.get(c.get("threat_level", "low"), "🟢 LOW")
        act = c.get("content_activity", {})
        act_str = (
            f"📝 {act.get('blog_count', 0)}&nbsp;"
            f"📣 {act.get('newsroom_count', 0)}&nbsp;"
            f"📰 {act.get('trade_press_count', 0)}"
        )
        rows += (
            f"<tr>"
            f"<td style='padding:10px;border:1px solid #e2e8f0;vertical-align:top'>"
            f"<strong>{c['name']}</strong><br>"
            f"<span style='color:#6b7280;font-size:11px'>{c.get('strategic_posture', '')}</span></td>"
            f"<td style='padding:10px;border:1px solid #e2e8f0'>{c.get('headline', '—')}</td>"
            f"<td style='padding:10px;border:1px solid #e2e8f0;text-align:center;font-size:11px'>{act_str}</td>"
            f"<td style='padding:10px;border:1px solid #e2e8f0;text-align:center'>{label}</td>"
            f"</tr>"
        )

    sections.append(
        f"<h2 style='color:#1e40af'>Competitor Snapshot</h2>"
        f"<table style='width:100%;border-collapse:collapse;font-size:13px'>"
        f"<thead><tr style='background:#f8fafc'>"
        f"<th style='padding:10px;border:1px solid #e2e8f0;text-align:left'>Competitor</th>"
        f"<th style='padding:10px;border:1px solid #e2e8f0;text-align:left'>Latest Development</th>"
        f"<th style='padding:10px;border:1px solid #e2e8f0;text-align:center'>Activity</th>"
        f"<th style='padding:10px;border:1px solid #e2e8f0'>Threat</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
        f"<p style='font-size:11px;color:#94a3b8;margin-top:6px'>"
        f"📝 Blog &nbsp;·&nbsp; 📣 Press / Product &nbsp;·&nbsp; 📰 Trade Press</p>"
    )

    high_threat = [c for c in competitors if c.get("threat_level") == "high"]
    if high_threat:
        dev_html = ""
        for c in high_threat:
            dev_html += f"<h3 style='color:#dc2626;margin-bottom:6px'>🔴 {c['name']}</h3>"
            for dev in c.get("developments", []):
                src = dev.get("source_type", "google")
                icon, lbl, color = SOURCE_ICONS.get(src, ("📰", "Trade Press", "#0891b2"))
                dev_html += (
                    f"<div style='border-left:3px solid {color};padding:8px 12px;"
                    f"margin-bottom:10px;background:#f8fafc'>"
                    f"<span style='font-size:11px;color:{color};font-weight:bold'>{icon} {lbl}</span><br>"
                    f"<strong style='font-size:13px'>{dev.get('title', '')}</strong> "
                    f"<span style='color:#94a3b8;font-size:11px'>{dev.get('date', '')}</span><br>"
                    f"<span style='font-size:13px'>{dev.get('summary', '')}</span><br>"
                    f"<span style='font-size:12px;color:#d97706'>"
                    f"<strong>SAS Impact:</strong> {dev.get('sas_impact', '')}</span>"
                    f"</div>"
                )
        sections.append(f"<h2 style='color:#1e40af'>High Threat — Detail</h2>{dev_html}")

    recs = data.get("recommendations", [])
    if recs:
        pri_colors = {"critical": "#dc2626", "high": "#d97706", "medium": "#2563eb"}
        rec_html = ""
        for r in recs:
            color = pri_colors.get(r.get("priority", "medium"), "#2563eb")
            rec_html += (
                f"<li style='margin-bottom:14px'>"
                f"<span style='color:{color};font-weight:bold'>[{r.get('priority','').upper()}]</span> "
                f"<strong>{r.get('area', '')}</strong><br>"
                f"<span style='font-size:13px'>{r.get('action', '')}</span><br>"
                f"<em style='color:#6b7280;font-size:12px'>{r.get('rationale', '')}</em>"
                f"</li>"
            )
        sections.append(
            f"<h2 style='color:#1e40af'>Strategic Recommendations</h2>"
            f"<ol style='padding-left:20px'>{rec_html}</ol>"
        )

    return (
        "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;"
        "max-width:780px;margin:0 auto;padding:28px;color:#1e293b'>"
        "<h1 style='color:#1e40af;margin-bottom:4px'>SAS Intelligent Decisioning</h1>"
        "<h2 style='font-weight:normal;color:#64748b;margin-top:0'>Competitive Intelligence Digest</h2>"
        f"<p style='color:#94a3b8;font-size:12px;border-bottom:1px solid #e2e8f0;"
        f"padding-bottom:16px'>Generated: {generated}</p>"
        + "\n".join(sections)
        + "<hr style='border:none;border-top:1px solid #e2e8f0;margin:28px 0'>"
        "<p style='font-size:11px;color:#94a3b8'>SAS Intel Feed &middot; Mon &amp; Thu "
        "&middot; Powered by Claude</p></body></html>"
    )


def send_email(data: dict) -> None:
    from_addr = os.getenv("EMAIL_FROM")
    to_addr = os.getenv("EMAIL_TO")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not all([from_addr, to_addr, password]):
        print("⚠  Email env vars not set. Skipping.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SAS Competitive Intel — {datetime.now().strftime('%b %d, %Y')}"
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(build_email_html(data), "html"))

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
    parser.add_argument("--dry-run", action="store_true", help="Fetch feeds only, skip Claude + email")
    parser.add_argument("--hours", type=int, default=LOOKBACK_HOURS, help="Lookback window in hours")
    parser.add_argument("--file", nargs="*", metavar="PATH", help="PDF/image files to attach as context")
    args = parser.parse_args()

    print(f"\nSAS Intel Feed  —  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Lookback: {args.hours}h  |  Competitors: {len(COMPETITORS)}\n")

    all_items: dict[str, list] = {}
    for comp in COMPETITORS:
        print(f"  {comp['name']}")
        items = fetch_competitor_items(comp, hours=args.hours)
        all_items[comp["name"]] = items
        counts = {"blog": 0, "newsroom": 0, "google": 0}
        for item in items:
            counts[item.get("source_type", "google")] += 1
        print(
            f"    → {len(items)} items  "
            f"[📝 {counts['blog']} blog  "
            f"📣 {counts['newsroom']} newsroom  "
            f"📰 {counts['google']} trade press]\n"
        )

    total = sum(len(v) for v in all_items.values())
    print(f"Total items collected: {total}")

    if args.dry_run:
        print("\n[dry-run] Skipping Claude analysis and email.")
        return

    print("\nRunning Claude analysis...")
    result = run_claude_analysis(all_items, context_files=args.file)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    save_json(result)
    send_email(result)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
