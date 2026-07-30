"""
fetch_intel.py — SAS Competitive Intelligence Feed (Battlecard Edition)

Usage:
    python fetch_intel.py                  # regular weekly run
    python fetch_intel.py --baseline       # one-time baseline run from Claude knowledge
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

from config import COMPETITORS, FEED_USER_AGENT, SYSTEM_PROMPT

load_dotenv()

FEED_FILE      = "intel_feed.json"
BASELINE_FILE  = "intel_baseline.json"
LOOKBACK_HOURS = 168  # one week — matches Monday-only cadence

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

    return deduped[:15]


# ── CLAUDE ANALYSIS ───────────────────────────────────────────────────────────

def parse_json(raw: str) -> dict:
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise ValueError(f"Could not parse JSON:\n{raw[:400]}")


def call_claude(prompt: str, system: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "max_tokens":
        print("  ⚠ Response truncated — retrying in concise mode...")
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": prompt + (
                "\n\nIMPORTANT: Be very concise. 1 sentence per field. "
                "Max 1 blog suggestion per competitor. Return only the JSON."
            )}],
        )
    return response.content[0].text


# ── BASELINE RUN ──────────────────────────────────────────────────────────────

BASELINE_SYSTEM = """You are a senior competitive intelligence strategist at SAS.

Generate a complete baseline battlecard for each of these 10 SAS Intelligent Decisioning competitors, based entirely on your training knowledge up to your cutoff date.

SAS Intelligent Decisioning context:
- Native SAS Viya integration: enterprise ML, statistical models, Python/R workflows
- Agentic AI with human-in-the-loop oversight; fully traceable agent actions
- Trustworthy AI: LIME/SHAP explainability, model lineage, audit trails
- End-to-end lifecycle: dev to test to prod, versioning, governance, approval workflows
- Industries: fraud detection, customer engagement, manufacturing, public sector
- Strengths: governance, explainability, regulated industry trust, enterprise scale
- Known gaps: no native knowledge graph (vs Quantexa); less fintech-native than Provenir/CRIF

Competitors to cover:
Sapiens, Palantir, Pegasystems, IBM, FICO, Provenir, ACTICO, CRIF, Aera Technology, Quantexa

Return ONLY valid JSON. No markdown fences, no preamble.

JSON schema:
{
  "generated_at": "<ISO 8601 timestamp>",
  "type": "baseline",
  "competitors": [
    {
      "name": "<exact name>",
      "segment": "<market segment>",
      "threat_level": "<high | medium | low>",
      "battlecard": {
        "tab1_approach_to_market": {
          "market_strategy": "<current go-to-market direction>",
          "customers": "<key customer segments and notable reference customers>",
          "verticals_served": "<industries actively targeted>",
          "partners": "<key technology and channel partners>"
        },
        "tab2_top_3_things_to_know": [
          "<most important fact for a sales rep #1>",
          "<most important fact for a sales rep #2>",
          "<most important fact for a sales rep #3>"
        ],
        "tab3_product_claims": {
          "overview": "<product summary, 2-3 sentences>",
          "key_claims": ["<major capability claim>"],
          "pricing_model": "<pricing approach if known, else null>"
        },
        "tab4_strengths_weaknesses": {
          "strengths": ["<strength relative to SAS ID>"],
          "weaknesses": ["<exploitable weakness relative to SAS ID>"],
          "differentiators": "<what genuinely sets them apart from SAS>"
        },
        "tab5_sales_strategies": {
          "what_to_attack": "<where SAS wins against this competitor>",
          "what_to_defend": "<where this competitor attacks SAS>",
          "trap_questions": [
            "<question that reveals this competitor weakness>",
            "<second trap question>"
          ]
        }
      }
    }
  ]
}

Be thorough and specific — this is the foundation every future weekly update will be compared against.
Accuracy matters more than brevity here. Use everything you know.
"""


def run_baseline() -> dict:
    print("\nGenerating baseline battlecards from Claude training knowledge...")
    print("(This may take 60-90 seconds — Claude is writing full profiles for all 10 competitors)\n")

    prompt = (
        "Generate complete baseline battlecards for all 10 SAS Intelligent Decisioning competitors: "
        "Sapiens, Palantir, Pegasystems, IBM, FICO, Provenir, ACTICO, CRIF, Aera Technology, Quantexa.\n\n"
        "Be thorough. This is the foundation all future weekly updates will be compared against.\n\n"
        "Return only the JSON."
    )

    raw = call_claude(prompt, BASELINE_SYSTEM)
    data = parse_json(raw)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["type"] = "baseline"
    return data


# ── WEEKLY DELTA RUN ──────────────────────────────────────────────────────────

def load_baseline() -> dict | None:
    try:
        with open(BASELINE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def build_delta_prompt(all_items: dict, baseline: dict | None, context_files: list | None) -> str:
    lines = [
        "TASK: Analyze new RSS articles from SAS Intelligent Decisioning competitors.",
        "Compare against the baseline knowledge provided.",
        "Only flag things that are GENUINELY NEW or CHANGED vs the baseline.",
        "Do not re-summarize stable, known facts.\n",
    ]

    if baseline:
        lines.append("## BASELINE KNOWLEDGE (what we already know — do not repeat this)")
        for comp in baseline.get("competitors", []):
            bc = comp.get("battlecard", {})
            tab3 = bc.get("tab3_product_claims", {})
            lines.append(
                f"- {comp['name']}: "
                f"{tab3.get('overview', 'No baseline overview.')}"
            )
        lines.append("")

    lines.append("## NEW RSS ARTICLES THIS WEEK\n")
    for comp_name, items in all_items.items():
        lines.append(f"### {comp_name}")
        if not items:
            lines.append("No new articles found this week.\n")
            continue
        for item in items:
            lines.append(
                f"- [{item['source_type'].upper()}] {item['title']} ({item['published']})"
            )
            if item["summary"]:
                lines.append(f"  {item['summary'][:350]}")
        lines.append("")

    if context_files:
        lines.append("## Additional Context Documents")
        for p in context_files:
            lines.append(f"- {p} (attached)")

    lines.append("\nReturn only the JSON. No preamble.")
    return "\n".join(lines)


def run_delta_analysis(all_items: dict, context_files: list | None = None) -> dict:
    baseline = load_baseline()
    if baseline:
        print(f"  ✓ Baseline loaded ({baseline.get('generated_at','unknown date')[:10]})")
    else:
        print("  ⚠ No baseline found — running without delta comparison.")
        print("    Tip: run 'python fetch_intel.py --baseline' to generate one.\n")

    prompt_text = build_delta_prompt(all_items, baseline, context_files)
    message_content = [{"type": "text", "text": prompt_text}]

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
            print(f"  Warning: could not attach {path}: {e}")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message_content}],
    )

    if response.stop_reason == "max_tokens":
        print("  ⚠ Response truncated — retrying in concise mode...")
        concise = prompt_text + (
            "\n\nIMPORTANT: Be very concise. 1 sentence per field. "
            "Max 1 blog suggestion per competitor. Return only the JSON."
        )
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": [{"type": "text", "text": concise}]}],
        )

    return parse_json(response.content[0].text)


# ── JSON OUTPUT ───────────────────────────────────────────────────────────────

def save_json(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved → {path}")


# ── EMAIL BUILDER ─────────────────────────────────────────────────────────────

def _td(content: str, align: str = "left", color: str = "") -> str:
    style = (
        f"padding:8px 10px;border:1px solid #e2e8f0;"
        f"vertical-align:top;text-align:{align};"
    )
    if color:
        style += f"color:{color};"
    return f"<td style='{style}'>{content}</td>"


def _th(content: str, align: str = "left") -> str:
    return (
        f"<th style='padding:8px 10px;border:1px solid #e2e8f0;background:#f1f5f9;"
        f"text-align:{align};font-size:11px;letter-spacing:.5px;color:#475569'>"
        f"{content}</th>"
    )


def _section(title: str, content: str) -> str:
    return (
        f"<h2 style='color:#1e40af;margin-top:28px;margin-bottom:10px;font-size:16px'>"
        f"{title}</h2>{content}"
    )


def _changed_badge(changed: bool) -> str:
    if changed:
        return "<span style='color:#dc2626;font-size:10px;font-weight:bold'>▲ CHANGED</span>"
    return "<span style='color:#94a3b8;font-size:10px'>— stable</span>"


def _ul(items: list) -> str:
    if not items:
        return "<span style='color:#94a3b8;font-size:12px'>None noted</span>"
    lis = "".join(f"<li style='margin-bottom:3px'>{i}</li>" for i in items if i)
    return f"<ul style='margin:4px 0;padding-left:16px;font-size:12px'>{lis}</ul>"


def build_baseline_email_html(data: dict) -> str:
    generated = data.get("generated_at", "")
    competitors = data.get("competitors", [])
    competitors_sorted = sorted(
        competitors,
        key=lambda c: THREAT_ORDER.get(c.get("threat_level", "low"), 2),
    )

    cards = ""
    for c in competitors_sorted:
        threat = c.get("threat_level", "low")
        color = THREAT_COLORS.get(threat, "#16a34a")
        bc = c.get("battlecard", {})
        tab1 = bc.get("tab1_approach_to_market", {})
        tab2 = bc.get("tab2_top_3_things_to_know", [])
        tab3 = bc.get("tab3_product_claims", {})
        tab4 = bc.get("tab4_strengths_weaknesses", {})
        tab5 = bc.get("tab5_sales_strategies", {})

        rows = (
            f"<tr style='background:#fafafa'>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;width:28%;vertical-align:top'>"
            f"<strong>Tab 1 — Approach to Market</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
            f"<strong>Strategy:</strong> {tab1.get('market_strategy','—')}<br>"
            f"<strong>Customers:</strong> {tab1.get('customers','—')}<br>"
            f"<strong>Verticals:</strong> {tab1.get('verticals_served','—')}<br>"
            f"<strong>Partners:</strong> {tab1.get('partners','—')}"
            f"</td></tr>"

            f"<tr>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
            f"<strong>Tab 2 — Top 3 Things to Know</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0'>{_ul(tab2)}</td></tr>"

            f"<tr style='background:#fafafa'>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
            f"<strong>Tab 3 — Product Claims</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
            f"{tab3.get('overview','—')}<br><br>"
            f"<strong>Key Claims:</strong>{_ul(tab3.get('key_claims',[]))}"
            f"</td></tr>"

            f"<tr>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
            f"<strong>Tab 4 — Strengths &amp; Weaknesses</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
            f"<strong>Strengths:</strong>{_ul(tab4.get('strengths',[]))}"
            f"<strong>Weaknesses:</strong>{_ul(tab4.get('weaknesses',[]))}"
            f"<strong>Differentiator:</strong> <em>{tab4.get('differentiators','—')}</em>"
            f"</td></tr>"

            f"<tr style='background:#fafafa'>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
            f"<strong>Tab 5 — Sales Strategies</strong></td>"
            f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
            f"<strong style='color:#16a34a'>⚔ Attack:</strong> {tab5.get('what_to_attack','—')}<br><br>"
            f"<strong style='color:#dc2626'>🛡 Defend:</strong> {tab5.get('what_to_defend','—')}<br><br>"
            f"<strong>Trap Questions:</strong>{_ul(tab5.get('trap_questions',[]))}"
            f"</td></tr>"
        )

        cards += (
            f"<div style='margin-bottom:28px;border:1px solid {color};border-top:3px solid {color}'>"
            f"<div style='padding:10px 14px;background:#f8fafc'>"
            f"<strong style='color:{color};font-size:15px'>{c['name']}</strong>"
            f" &nbsp; {THREAT_LABELS.get(threat,'')} &nbsp;"
            f"<span style='color:#64748b;font-size:12px'>{c.get('segment','')}</span>"
            f"</div>"
            f"<table style='width:100%;border-collapse:collapse;font-size:12px'>{rows}</table>"
            f"</div>"
        )

    return (
        "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;"
        "max-width:820px;margin:0 auto;padding:28px;color:#1e293b'>"
        "<h1 style='color:#1e40af;margin-bottom:2px'>SAS Intelligent Decisioning</h1>"
        "<h2 style='font-weight:normal;color:#64748b;margin-top:0;font-size:15px'>"
        "Competitive Baseline Battlecards</h2>"
        "<div style='background:#fef3c7;border:1px solid #f59e0b;padding:10px 14px;"
        "font-size:12px;margin-bottom:20px'>"
        "📚 <strong>This is your baseline.</strong> Generated from Claude's training knowledge. "
        "All future weekly digests will compare against this and only surface what has changed."
        "</div>"
        f"<p style='color:#94a3b8;font-size:11px;border-bottom:1px solid #e2e8f0;"
        f"padding-bottom:14px'>Generated: {generated}</p>"
        + cards
        + "<hr style='border:none;border-top:1px solid #e2e8f0;margin:28px 0'>"
        "<p style='font-size:11px;color:#94a3b8'>"
        "SAS Intel Feed &middot; Baseline Run &middot; Powered by Claude</p>"
        "</body></html>"
    )


def build_delta_email_html(data: dict) -> str:
    generated = data.get("generated_at", "")
    sections = []

    signals = data.get("market_signals", [])
    if signals:
        bullets = "".join(
            f"<li style='margin-bottom:5px;font-size:13px'>{s}</li>" for s in signals
        )
        sections.append(
            _section("📡 Market Signals", f"<ul style='padding-left:18px'>{bullets}</ul>")
        )

    competitors = sorted(
        data.get("competitors", []),
        key=lambda c: THREAT_ORDER.get(c.get("threat_level", "low"), 2),
    )

    # Summary table
    summary_rows = ""
    for c in competitors:
        threat = c.get("threat_level", "low")
        color = THREAT_COLORS.get(threat, "#16a34a")
        act = c.get("content_activity", {})
        has_updates = c.get("has_updates", False)
        bc = c.get("battlecard", {})
        tab1 = bc.get("tab1_approach_to_market", {})
        tab3 = bc.get("tab3_product_claims", {})
        update_flag = (
            "<span style='color:#dc2626;font-weight:bold'>▲ Updated</span>"
            if has_updates else
            "<span style='color:#94a3b8'>— No change</span>"
        )
        activity = (
            f"📝{act.get('blog_count',0)} "
            f"📣{act.get('newsroom_count',0)} "
            f"📰{act.get('trade_press_count',0)}"
        )
        summary_rows += (
            f"<tr>"
            + _td(
                f"<strong style='color:{color}'>{c['name']}</strong><br>"
                f"<span style='font-size:11px;color:#64748b'>{c.get('segment','')}</span>"
            )
            + _td(THREAT_LABELS.get(threat, "🟢 LOW"), align="center")
            + _td(update_flag, align="center")
            + _td(_changed_badge(tab1.get("changed", False)), align="center")
            + _td(_changed_badge(tab3.get("changed", False)), align="center")
            + _td(activity, align="center")
            + "</tr>"
        )

    sections.append(
        _section("Competitor Snapshot",
            "<table style='width:100%;border-collapse:collapse;font-size:12px'>"
            "<thead><tr>"
            + _th("Competitor")
            + _th("Threat", align="center")
            + _th("Updates", align="center")
            + _th("Market Approach", align="center")
            + _th("Product Claims", align="center")
            + _th("Activity", align="center")
            + "</tr></thead>"
            + f"<tbody>{summary_rows}</tbody></table>"
            + "<p style='font-size:11px;color:#94a3b8;margin-top:4px'>"
            + "📝 Blog &nbsp;·&nbsp; 📣 Press &nbsp;·&nbsp; 📰 Trade Press</p>"
        )
    )

    # Battlecard detail — only updated competitors
    updated = [c for c in competitors if c.get("has_updates")]
    if updated:
        detail_html = ""
        for c in updated:
            threat = c.get("threat_level", "low")
            color = THREAT_COLORS.get(threat, "#16a34a")
            bc = c.get("battlecard", {})
            tab1 = bc.get("tab1_approach_to_market", {})
            tab2 = bc.get("tab2_top_3_things_to_know", [])
            tab3 = bc.get("tab3_product_claims", {})
            tab4 = bc.get("tab4_strengths_weaknesses", {})
            tab5 = bc.get("tab5_sales_strategies", {})

            new_claims = tab3.get("new_claims", [])
            pricing = tab3.get("pricing_signals")

            rows = (
                f"<tr style='background:#fafafa'>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;width:28%;vertical-align:top'>"
                f"<strong>Tab 1 — Approach to Market</strong><br>{_changed_badge(tab1.get('changed',False))}</td>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
                f"<strong>Strategy:</strong> {tab1.get('market_strategy','—')}<br>"
                f"<strong>Customers:</strong> {tab1.get('customers','—')}<br>"
                f"<strong>Verticals:</strong> {tab1.get('verticals_served','—')}<br>"
                f"<strong>Partners:</strong> {tab1.get('partners','—')}"
                f"</td></tr>"

                f"<tr>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
                f"<strong>Tab 2 — Top 3 to Know</strong></td>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0'>{_ul(tab2)}</td></tr>"

                f"<tr style='background:#fafafa'>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
                f"<strong>Tab 3 — Product Claims</strong><br>{_changed_badge(tab3.get('changed',False))}</td>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
                f"{tab3.get('overview','—')}"
                + (f"<br><br><strong>New This Week:</strong>{_ul(new_claims)}" if new_claims else "")
                + (f"<br><strong>Pricing Signal:</strong> {pricing}" if pricing else "")
                + "</td></tr>"

                f"<tr>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
                f"<strong>Tab 4 — Strengths &amp; Weaknesses</strong></td>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
                f"<strong>Strengths:</strong>{_ul(tab4.get('strengths',[]))}"
                f"<strong>Weaknesses:</strong>{_ul(tab4.get('weaknesses',[]))}"
                f"<em style='font-size:12px'>{tab4.get('differentiators','')}</em>"
                f"</td></tr>"

                f"<tr style='background:#fafafa'>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;vertical-align:top'>"
                f"<strong>Tab 5 — Sales Strategies</strong></td>"
                f"<td style='padding:8px 10px;border:1px solid #e2e8f0;font-size:12px'>"
                f"<strong style='color:#16a34a'>⚔ Attack:</strong> {tab5.get('what_to_attack','—')}<br><br>"
                f"<strong style='color:#dc2626'>🛡 Defend:</strong> {tab5.get('what_to_defend','—')}<br><br>"
                f"<strong>Trap Questions:</strong>{_ul(tab5.get('trap_questions',[]))}"
                f"</td></tr>"
            )

            detail_html += (
                f"<div style='margin-bottom:24px;border:1px solid {color};border-top:3px solid {color}'>"
                f"<div style='padding:8px 12px;background:#f8fafc'>"
                f"<strong style='color:{color};font-size:14px'>{c['name']}</strong>"
                f" &nbsp; {THREAT_LABELS.get(threat,'')} &nbsp;"
                f"<span style='color:#64748b;font-size:12px'>{c.get('segment','')}</span>"
                f"</div>"
                f"<table style='width:100%;border-collapse:collapse;font-size:12px'>{rows}</table>"
                f"</div>"
            )

        sections.append(_section("📋 What Changed This Week", detail_html))
    else:
        sections.append(
            _section(
                "📋 What Changed This Week",
                "<p style='color:#64748b;font-size:13px'>"
                "No significant changes detected vs baseline this week.</p>"
            )
        )

    # Blog suggestions
    all_blogs = [
        (c["name"], b)
        for c in competitors
        for b in c.get("blog_suggestions", [])
        if b.get("title")
    ]
    if all_blogs:
        blog_rows = ""
        for comp_name, b in all_blogs:
            blog_rows += (
                f"<tr>"
                + _td(f"<em style='color:#64748b;font-size:11px'>{comp_name}</em>")
                + _td(
                    f"<strong style='font-size:13px'>{b.get('title','')}</strong><br>"
                    f"<span style='font-size:12px;color:#374151'>{b.get('angle','')}</span>"
                )
                + _td(f"<span style='font-size:11px;color:#6366f1'>{b.get('why_now','')}</span>")
                + "</tr>"
            )
        sections.append(
            _section("✍️ Suggested Blog Posts",
                "<table style='width:100%;border-collapse:collapse;font-size:12px'>"
                "<thead><tr>"
                + _th("In Response To")
                + _th("Suggested Title &amp; Angle")
                + _th("Why Now")
                + "</tr></thead>"
                + f"<tbody>{blog_rows}</tbody></table>"
                + "<p style='font-size:11px;color:#94a3b8;margin-top:6px'>"
                + "Posts do not name competitors directly.</p>"
            )
        )

    return (
        "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;"
        "max-width:820px;margin:0 auto;padding:28px;color:#1e293b'>"
        "<h1 style='color:#1e40af;margin-bottom:2px'>SAS Intelligent Decisioning</h1>"
        "<h2 style='font-weight:normal;color:#64748b;margin-top:0;font-size:15px'>"
        "Weekly Competitive Intelligence</h2>"
        f"<p style='color:#94a3b8;font-size:11px;border-bottom:1px solid #e2e8f0;"
        f"padding-bottom:14px'>Generated: {generated}</p>"
        + "\n".join(sections)
        + "<hr style='border:none;border-top:1px solid #e2e8f0;margin:28px 0'>"
        "<p style='font-size:11px;color:#94a3b8'>"
        "SAS Intel Feed &middot; Weekly Monday &middot; Powered by Claude</p>"
        "</body></html>"
    )


# ── EMAIL SEND ────────────────────────────────────────────────────────────────

def send_email(subject: str, html: str) -> None:
    api_key = os.getenv("SENDGRID_API_KEY")
    from_addr = os.getenv("EMAIL_FROM")
    to_addr = os.getenv("EMAIL_TO")

    if not all([api_key, from_addr, to_addr]):
        print("⚠  SendGrid env vars not set. Skipping email.")
        return

    recipients = [addr.strip() for addr in to_addr.split(",")]

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
        response = sg.send(msg)
        print(f"✓ Email sent → {', '.join(recipients)} (status {response.status_code})")
    except Exception as e:
        print(f"✗ Email failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SAS Intel Feed — Battlecard Edition")
    parser.add_argument("--baseline", action="store_true",
                        help="Generate full baseline battlecards from Claude knowledge (run once)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch feeds only; skip Claude + email")
    parser.add_argument("--hours", type=int, default=LOOKBACK_HOURS,
                        help="Lookback window in hours")
    parser.add_argument("--file", nargs="*", metavar="PATH",
                        help="PDF/image files to attach as context")
    args = parser.parse_args()

    print(f"\nSAS Intel Feed  —  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    # ── BASELINE MODE ─────────────────────────────────────────────────────────
    if args.baseline:
        print("Mode: BASELINE\n")
        data = run_baseline()
        save_json(data, BASELINE_FILE)
        date_str = datetime.now().strftime("%b %d, %Y")
        send_email(
            subject=f"SAS Competitive Baseline Battlecards — {date_str}",
            html=build_baseline_email_html(data),
        )
        print("\nBaseline complete. Run 'python fetch_intel.py' for weekly delta runs.\n")
        return

    # ── WEEKLY DELTA MODE ─────────────────────────────────────────────────────
    print(f"Mode: WEEKLY DELTA  |  Lookback: {args.hours}h  |  Competitors: {len(COMPETITORS)}\n")

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
            f"[📝 {counts['blog']}  📣 {counts['newsroom']}  📰 {counts['google']}]\n"
        )

    total = sum(len(v) for v in all_items.values())
    print(f"Total items collected: {total}")

    if args.dry_run:
        print("\n[dry-run] Skipping Claude analysis and email.")
        return

    print("\nRunning Claude analysis...")
    result = run_delta_analysis(all_items, context_files=args.file)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    save_json(result, FEED_FILE)

    date_str = datetime.now().strftime("%b %d, %Y")
    send_email(
        subject=f"SAS Competitive Intel — {date_str}",
        html=build_delta_email_html(result),
    )

    print("\nDone.\n")


if __name__ == "__main__":
    main()
