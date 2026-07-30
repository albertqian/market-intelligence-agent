"""
fetch_intel.py — SAS Competitive Intelligence Feed (Battlecard Edition)

Usage:
    python fetch_intel.py                  # regular weekly delta run
    python fetch_intel.py --baseline       # one-time baseline from Claude knowledge
    python fetch_intel.py --dry-run        # fetch feeds only, skip Claude + email
    python fetch_intel.py --hours 168      # extend lookback window
    python fetch_intel.py --file report.pdf  # attach context document
"""

import argparse
import base64
import json
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import anthropic
import feedparser
from dotenv import load_dotenv

from config import BASELINE_SYSTEM, COMPETITORS, DELTA_SYSTEM, FEED_USER_AGENT

load_dotenv()

FEED_FILE     = "intel_feed.json"
BASELINE_FILE = "intel_baseline.json"
LOOKBACK_HOURS = 168

SOURCE_LABELS = {
    "blog":     "📝 Thought Leadership",
    "newsroom": "📣 Product / Company Update",
    "google":   "📰 Trade Press",
}

THREAT_ORDER  = {"high": 0, "medium": 1, "low": 2}
THREAT_LABELS = {"high": "🔴 HIGH", "medium": "🟡 MED", "low": "🟢 LOW"}
THREAT_COLORS = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}


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
        for entry in feed.entries[:8]:
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
                "summary": (entry.get("summary") or "")[:400].strip(),
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
            print(f"      ✓ {len(items)} [{SOURCE_LABELS.get(feed_cfg['type'], '')}]")
        all_items.extend(items)
        time.sleep(0.3)

    for query in competitor.get("google_news_queries", []):
        items = fetch_feed(google_news_url(query), "google", cutoff)
        if items:
            print(f"      ✓ {len(items)} [📰 Trade Press] via: '{query}'")
        all_items.extend(items)
        time.sleep(0.3)

    seen, deduped = set(), []
    for item in all_items:
        key = item["title"].lower()[:80]
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:10]


# ── CLAUDE HELPERS ────────────────────────────────────────────────────────────

def parse_json(raw: str) -> dict:
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise ValueError(f"Could not parse JSON:\n{raw[:400]}")


def call_claude(prompt: str, system: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "max_tokens":
        print("  ⚠ Truncated — retrying in concise mode...")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": prompt + (
                "\n\nCRITICAL: Response was truncated. Be extremely concise — "
                "max 1 sentence per field. Return only valid JSON for the "
                "competitors listed. Stop after closing brace."
            )}],
        )
    return parse_json(response.content[0].text)


# ── BASELINE RUN ──────────────────────────────────────────────────────────────

def run_baseline() -> dict:
    print("\nGenerating baseline battlecards (2 batches of 5)...\n")

    batches = [
        ["Sapiens", "Palantir", "Pegasystems", "IBM", "FICO"],
        ["Provenir", "ACTICO", "CRIF", "Aera Technology", "Quantexa"],
    ]

    all_competitors = []
    for i, batch in enumerate(batches, 1):
        names = ", ".join(batch)
        print(f"  Batch {i}/2: {names}")
        prompt = (
            f"Generate baseline battlecards for ONLY these 5 competitors: {names}.\n"
            "Return ONLY the JSON with a competitors array containing exactly 5 entries.\n"
            "Keep every text field to 1-2 sentences maximum."
        )
        result = call_claude(prompt, BASELINE_SYSTEM)
        comps = result.get("competitors", [])
        print(f"    ✓ {len(comps)} returned")
        all_competitors.extend(comps)
        time.sleep(3)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "type": "baseline",
        "competitors": all_competitors,
    }


# ── WEEKLY DELTA RUN ──────────────────────────────────────────────────────────

def load_baseline() -> dict | None:
    try:
        with open(BASELINE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def run_delta_analysis(all_items: dict, context_files: list | None = None) -> dict:
    baseline = load_baseline()
    if baseline:
        print(f"  ✓ Baseline loaded ({baseline.get('generated_at','')[:10]})")
    else:
        print("  ⚠ No baseline — run --baseline first for best results")

    batches = [
        ["Sapiens", "Palantir", "Pegasystems", "IBM", "FICO"],
        ["Provenir", "ACTICO", "CRIF", "Aera Technology", "Quantexa"],
    ]

    all_competitors = []
    all_signals = []

    for i, batch_names in enumerate(batches, 1):
        print(f"  Analyzing batch {i}/2: {', '.join(batch_names)}")

        lines = [
            f"Analyze new RSS articles for ONLY these competitors: {', '.join(batch_names)}.",
            "Return JSON with ONLY these competitor names in the competitors array.\n",
            "## NEW RSS ARTICLES\n",
        ]

        for name in batch_names:
            items = all_items.get(name, [])
            lines.append(f"### {name}")
            if not items:
                lines.append("No new articles this week.\n")
                continue
            for item in items:
                lines.append(f"- [{item['source_type'].upper()}] {item['title']} ({item['published']})")
                if item["summary"]:
                    lines.append(f"  {item['summary'][:250]}")
            lines.append("")

        if baseline and i == 1:
            lines.append("## WHAT WE ALREADY KNOW (do not repeat)\n")
            for comp in baseline.get("competitors", []):
                if comp["name"] in batch_names:
                    bc = comp.get("battlecard", {})
                    tab3 = bc.get("tab3_product_claims", {})
                    lines.append(f"- {comp['name']}: {tab3.get('overview', '')}")

        lines.append("\nReturn only the JSON. Be concise — 1 sentence per field.")
        prompt = "\n".join(lines)

        result = call_claude(prompt, DELTA_SYSTEM)
        comps = result.get("competitors", [])
        sigs = result.get("market_signals", [])
        print(f"    ✓ {len(comps)} competitors, {len(sigs)} signals")
        all_competitors.extend(comps)
        all_signals.extend(sigs)
        time.sleep(3)

    # Deduplicate signals
    seen, unique = set(), []
    for s in all_signals:
        if s.lower()[:40] not in seen:
            seen.add(s.lower()[:40])
            unique.append(s)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_signals": unique[:4],
        "competitors": all_competitors,
    }


# ── JSON SAVE ─────────────────────────────────────────────────────────────────

def save_json(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved → {path}")


# ── EMAIL BUILDERS ────────────────────────────────────────────────────────────

def _th(text: str, align: str = "left") -> str:
    return (
        f"<th style='padding:8px 10px;border:1px solid #e2e8f0;background:#f1f5f9;"
        f"font-size:11px;color:#475569;text-align:{align}'>{text}</th>"
    )

def _td(text: str, align: str = "left", color: str = "") -> str:
    style = f"padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top;text-align:{align};"
    if color:
        style += f"color:{color};"
    return f"<td style='{style}'>{text}</td>"

def _ul(items: list) -> str:
    if not items:
        return "<span style='color:#94a3b8;font-size:12px'>None noted</span>"
    lis = "".join(f"<li style='margin-bottom:3px'>{i}</li>" for i in items if i)
    return f"<ul style='margin:4px 0;padding-left:16px;font-size:12px'>{lis}</ul>"

def _section(title: str, body: str) -> str:
    return (
        f"<h2 style='color:#1e40af;font-size:16px;margin-top:28px;margin-bottom:10px'>"
        f"{title}</h2>{body}"
    )

def _changed(val: bool) -> str:
    return (
        "<span style='color:#dc2626;font-size:10px;font-weight:bold'>▲ CHANGED</span>"
        if val else
        "<span style='color:#94a3b8;font-size:10px'>— stable</span>"
    )


def build_baseline_email(data: dict) -> str:
    competitors = sorted(
        data.get("competitors", []),
        key=lambda c: THREAT_ORDER.get(c.get("threat_level", "low"), 2),
    )
    cards = ""
    for c in competitors:
        threat = c.get("threat_level", "low")
        color = THREAT_COLORS.get(threat, "#16a34a")
        bc = c.get("battlecard", {})
        t1 = bc.get("tab1_approach_to_market", {})
        t2 = bc.get("tab2_top_3_things_to_know", [])
        t3 = bc.get("tab3_product_claims", {})
        t4 = bc.get("tab4_strengths_weaknesses", {})
        t5 = bc.get("tab5_sales_strategies", {})

        rows = "".join([
            f"<tr style='background:#fafafa'><td style='padding:8px 10px;border:1px solid #e2e8f0;width:25%;vertical-align:top;font-size:12px'><strong>Tab 1 — Market Approach</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
            f"<strong>Strategy:</strong> {t1.get('market_strategy','—')}<br>"
            f"<strong>Customers:</strong> {t1.get('customers','—')}<br>"
            f"<strong>Verticals:</strong> {t1.get('verticals_served','—')}<br>"
            f"<strong>Partners:</strong> {t1.get('partners','—')}</td></tr>",

            f"<tr><td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px;vertical-align:top'><strong>Tab 2 — Top 3 to Know</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0'>{_ul(t2)}</td></tr>",

            f"<tr style='background:#fafafa'><td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px;vertical-align:top'><strong>Tab 3 — Product Claims</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>{t3.get('overview','—')}<br><br>"
            f"<strong>Key Claims:</strong>{_ul(t3.get('key_claims',[]))}</td></tr>",

            f"<tr><td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px;vertical-align:top'><strong>Tab 4 — Strengths &amp; Weaknesses</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
            f"<strong>Strengths:</strong>{_ul(t4.get('strengths',[]))}"
            f"<strong>Weaknesses:</strong>{_ul(t4.get('weaknesses',[]))}"
            f"<em>{t4.get('differentiators','')}</em></td></tr>",

            f"<tr style='background:#fafafa'><td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px;vertical-align:top'><strong>Tab 5 — Sales Strategies</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
            f"<strong style='color:#16a34a'>⚔ Attack:</strong> {t5.get('what_to_attack','—')}<br><br>"
            f"<strong style='color:#dc2626'>🛡 Defend:</strong> {t5.get('what_to_defend','—')}<br><br>"
            f"<strong>Trap Questions:</strong>{_ul(t5.get('trap_questions',[]))}</td></tr>",
        ])

        cards += (
            f"<div style='margin-bottom:24px;border:1px solid {color};border-top:3px solid {color}'>"
            f"<div style='padding:8px 14px;background:#f8fafc'>"
            f"<strong style='color:{color};font-size:14px'>{c['name']}</strong>"
            f" &nbsp; {THREAT_LABELS.get(threat,'')} &nbsp;"
            f"<span style='color:#64748b;font-size:12px'>{c.get('segment','')}</span>"
            f"</div>"
            f"<table style='width:100%;border-collapse:collapse'>{rows}</table>"
            f"</div>"
        )

    return (
        "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;max-width:820px;margin:0 auto;padding:28px;color:#1e293b'>"
        "<h1 style='color:#1e40af;margin-bottom:2px'>SAS Intelligent Decisioning</h1>"
        "<h2 style='font-weight:normal;color:#64748b;margin-top:0;font-size:15px'>Competitive Baseline Battlecards</h2>"
        "<div style='background:#fef3c7;border:1px solid #f59e0b;padding:10px 14px;font-size:12px;margin-bottom:20px'>"
        "📚 <strong>This is your baseline.</strong> All future weekly digests compare against this and only surface what changed."
        "</div>"
        f"<p style='color:#94a3b8;font-size:11px;border-bottom:1px solid #e2e8f0;padding-bottom:14px'>Generated: {data.get('generated_at','')}</p>"
        + cards
        + "<hr style='border:none;border-top:1px solid #e2e8f0;margin:28px 0'>"
        "<p style='font-size:11px;color:#94a3b8'>SAS Intel Feed · Baseline · Powered by Claude</p>"
        "</body></html>"
    )


def build_delta_email(data: dict) -> str:
    sections = []
    generated = data.get("generated_at", "")

    # Market signals
    signals = data.get("market_signals", [])
    if signals:
        bullets = "".join(f"<li style='margin-bottom:5px;font-size:13px'>{s}</li>" for s in signals)
        sections.append(_section("📡 Market Signals", f"<ul style='padding-left:18px'>{bullets}</ul>"))

    competitors = sorted(
        data.get("competitors", []),
        key=lambda c: THREAT_ORDER.get(c.get("threat_level", "low"), 2),
    )

    # Snapshot table
    rows = ""
    for c in competitors:
        threat = c.get("threat_level", "low")
        color = THREAT_COLORS.get(threat, "#16a34a")
        act = c.get("content_activity", {})
        changes = c.get("changes", {})
        has_updates = c.get("has_updates", False)
        update_str = (
            "<span style='color:#dc2626;font-weight:bold'>▲ Updated</span>"
            if has_updates else
            "<span style='color:#94a3b8'>— No change</span>"
        )
        rows += (
            f"<tr>"
            + _td(f"<strong style='color:{color}'>{c['name']}</strong><br><span style='font-size:11px;color:#64748b'>{c.get('segment','')}</span>")
            + _td(THREAT_LABELS.get(threat, "🟢 LOW"), align="center")
            + _td(update_str, align="center")
            + _td(_changed(changes.get("market_approach_changed", False)), align="center")
            + _td(_changed(changes.get("product_claims_changed", False)), align="center")
            + _td(f"📝{act.get('blog_count',0)} 📣{act.get('newsroom_count',0)} 📰{act.get('trade_press_count',0)}", align="center")
            + "</tr>"
        )

    snapshot = (
        "<table style='width:100%;border-collapse:collapse;font-size:12px'>"
        "<thead><tr>"
        + _th("Competitor") + _th("Threat", "center") + _th("Updates", "center")
        + _th("Market Approach", "center") + _th("Product Claims", "center") + _th("Activity", "center")
        + "</tr></thead><tbody>" + rows + "</tbody></table>"
        + "<p style='font-size:11px;color:#94a3b8;margin-top:4px'>📝 Blog · 📣 Press · 📰 Trade Press</p>"
    )
    sections.append(_section("Competitor Snapshot", snapshot))

    # What changed — detail for updated competitors only
    updated = [c for c in competitors if c.get("has_updates")]
    if updated:
        detail = ""
        for c in updated:
            threat = c.get("threat_level", "low")
            color = THREAT_COLORS.get(threat, "#16a34a")
            changes = c.get("changes", {})
            t2 = c.get("tab2_top_3_things_to_know", [])
            new_claims = c.get("new_product_claims", [])
            sales = c.get("sales_impact", {})

            inner = (
                f"<strong style='color:{color}'>{c['name']}</strong> &nbsp; {THREAT_LABELS.get(threat,'')}<br>"
                f"<em style='font-size:12px;color:#64748b'>{changes.get('what_changed','')}</em>"
                f"<br><br>"
            )

            if t2:
                inner += f"<strong style='font-size:11px'>Top 3 This Week:</strong>{_ul(t2)}"

            if new_claims:
                inner += f"<strong style='font-size:11px'>New Product Claims:</strong>{_ul(new_claims)}"

            if sales:
                inner += (
                    f"<div style='margin-top:8px;font-size:12px'>"
                    f"<strong style='color:#16a34a'>⚔ Attack:</strong> {sales.get('what_to_attack','—')}<br>"
                    f"<strong style='color:#dc2626'>🛡 Defend:</strong> {sales.get('what_to_defend','—')}<br>"
                    f"<strong>Trap:</strong> {sales.get('trap_question','—')}"
                    f"</div>"
                )

            detail += (
                f"<div style='border-left:3px solid {color};padding:10px 14px;"
                f"margin-bottom:12px;background:#fafafa'>{inner}</div>"
            )

        sections.append(_section("📋 What Changed This Week", detail))
    else:
        sections.append(_section(
            "📋 What Changed This Week",
            "<p style='color:#64748b;font-size:13px'>No significant changes detected vs baseline this week.</p>"
        ))

    # Blog suggestions
    blogs = [(c["name"], c["blog_suggestion"]) for c in competitors if c.get("blog_suggestion") and c.get("has_updates")]
    if blogs:
        blog_rows = ""
        for comp_name, b in blogs:
            blog_rows += (
                "<tr>"
                + _td(f"<em style='color:#64748b;font-size:11px'>{comp_name}</em>")
                + _td(f"<strong style='font-size:13px'>{b.get('title','')}</strong><br><span style='font-size:12px;color:#374151'>{b.get('angle','')}</span>")
                + _td(f"<span style='font-size:11px;color:#6366f1'>{b.get('why_now','')}</span>")
                + "</tr>"
            )
        sections.append(_section(
            "✍️ Suggested Blog Posts",
            "<table style='width:100%;border-collapse:collapse;font-size:12px'>"
            "<thead><tr>" + _th("In Response To") + _th("Title &amp; Angle") + _th("Why Now") + "</tr></thead>"
            + f"<tbody>{blog_rows}</tbody></table>"
            + "<p style='font-size:11px;color:#94a3b8;margin-top:6px'>Posts do not name competitors directly.</p>"
        ))

    return (
        "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;max-width:820px;margin:0 auto;padding:28px;color:#1e293b'>"
        "<h1 style='color:#1e40af;margin-bottom:2px'>SAS Intelligent Decisioning</h1>"
        "<h2 style='font-weight:normal;color:#64748b;margin-top:0;font-size:15px'>Weekly Competitive Intelligence</h2>"
        f"<p style='color:#94a3b8;font-size:11px;border-bottom:1px solid #e2e8f0;padding-bottom:14px'>Generated: {generated}</p>"
        + "\n".join(sections)
        + "<hr style='border:none;border-top:1px solid #e2e8f0;margin:28px 0'>"
        "<p style='font-size:11px;color:#94a3b8'>SAS Intel Feed · Weekly Monday · Powered by Claude</p>"
        "</body></html>"
    )


# ── EMAIL SEND ────────────────────────────────────────────────────────────────

def send_email(subject: str, html: str) -> None:
    api_key  = os.getenv("SENDGRID_API_KEY")
    from_addr = os.getenv("EMAIL_FROM")
    to_addr   = os.getenv("EMAIL_TO")

    if not all([api_key, from_addr, to_addr]):
        print("⚠  SendGrid env vars not set. Skipping email.")
        return

    recipients = [a.strip() for a in to_addr.split(",")]

    import sendgrid
    from sendgrid.helpers.mail import Mail, To

    msg = Mail(
        from_email=from_addr,
        to_emails=[To(r) for r in recipients],
        subject=subject,
        html_content=html,
    )
    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        resp = sg.send(msg)
        print(f"✓ Email sent → {', '.join(recipients)} (status {resp.status_code})")
    except Exception as e:
        print(f"✗ Email failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SAS Intel Feed")
    parser.add_argument("--baseline", action="store_true", help="Generate full baseline battlecards")
    parser.add_argument("--dry-run",  action="store_true", help="Fetch feeds only, skip Claude + email")
    parser.add_argument("--hours",    type=int, default=LOOKBACK_HOURS, help="Lookback window in hours")
    parser.add_argument("--file",     nargs="*", metavar="PATH", help="PDF/image context files")
    args = parser.parse_args()

    print(f"\nSAS Intel Feed  —  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    date_str = datetime.now().strftime("%b %d, %Y")

    # ── BASELINE ──────────────────────────────────────────────────────────────
    if args.baseline:
        print("Mode: BASELINE\n")
        data = run_baseline()
        save_json(data, BASELINE_FILE)
        send_email(
            subject=f"SAS Competitive Baseline Battlecards — {date_str}",
            html=build_baseline_email(data),
        )
        print("\nBaseline complete.\n")
        return

    # ── WEEKLY DELTA ──────────────────────────────────────────────────────────
    print(f"Mode: WEEKLY DELTA  |  Lookback: {args.hours}h  |  Competitors: {len(COMPETITORS)}\n")

    all_items: dict[str, list] = {}
    for comp in COMPETITORS:
        print(f"  {comp['name']}")
        items = fetch_competitor_items(comp, hours=args.hours)
        all_items[comp["name"]] = items
        counts = {"blog": 0, "newsroom": 0, "google": 0}
        for item in items:
            counts[item.get("source_type", "google")] += 1
        print(f"    → {len(items)} items [📝{counts['blog']} 📣{counts['newsroom']} 📰{counts['google']}]\n")

    total = sum(len(v) for v in all_items.values())
    print(f"Total items: {total}")

    if args.dry_run:
        print("\n[dry-run] Skipping Claude + email.")
        return

    print("\nRunning Claude analysis...")
    result = run_delta_analysis(all_items, context_files=args.file)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    save_json(result, FEED_FILE)
    send_email(
        subject=f"SAS Competitive Intel — {date_str}",
        html=build_delta_email(result),
    )
    print("\nDone.\n")


if __name__ == "__main__":
    main()
