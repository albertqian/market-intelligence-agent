"""
config.py — Competitor configuration and Claude system prompts.
Two separate prompts:
  BASELINE_SYSTEM — used once, generates full battlecards
  DELTA_SYSTEM    — used weekly, generates only changes and actions
"""

FEED_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

COMPETITORS = [
    {
        "name": "Sapiens",
        "segment": "Insurance / Financial",
        "feeds": [],
        "google_news_queries": [
            "Sapiens International software insurance AI",
            "Sapiens DECISION platform release",
        ],
    },
    {
        "name": "Palantir",
        "segment": "Government / Enterprise",
        "feeds": [
            {"url": "https://medium.com/feed/palantir", "type": "blog"},
        ],
        "google_news_queries": [
            "Palantir AIP platform product",
            "Palantir artificial intelligence enterprise",
        ],
    },
    {
        "name": "Pegasystems",
        "segment": "CRM / BPM",
        "feeds": [],
        "google_news_queries": [
            "Pegasystems Pega AI product launch",
            "Pega decisioning automation release",
        ],
    },
    {
        "name": "IBM",
        "segment": "Enterprise AI",
        "feeds": [
            {"url": "https://www.ibm.com/blog/feed/", "type": "blog"},
        ],
        "google_news_queries": [
            "IBM watsonx AI product announcement",
            "IBM decision optimization ODM release",
        ],
    },
    {
        "name": "FICO",
        "segment": "Credit / Risk",
        "feeds": [],
        "google_news_queries": [
            "FICO credit scoring AI platform",
            "FICO decision management product",
        ],
    },
    {
        "name": "Provenir",
        "segment": "Fintech",
        "feeds": [
            {"url": "https://www.provenir.com/feed/", "type": "blog"},
        ],
        "google_news_queries": [
            "Provenir fintech credit risk AI",
            "Provenir decisioning platform",
        ],
    },
    {
        "name": "ACTICO",
        "segment": "Compliance / Reg-Tech",
        "feeds": [],
        "google_news_queries": [
            "ACTICO decision management compliance AI",
            "ACTICO rules engine software",
        ],
    },
    {
        "name": "CRIF",
        "segment": "Credit Risk",
        "feeds": [],
        "google_news_queries": [
            "CRIF credit risk AI analytics platform",
            "CRIF decisioning GenAI",
        ],
    },
    {
        "name": "Aera Technology",
        "segment": "Supply Chain / Ops",
        "feeds": [],
        "google_news_queries": [
            "Aera Technology agentic AI supply chain",
            "Aera Technology decision automation",
        ],
    },
    {
        "name": "Quantexa",
        "segment": "AML / KYC / Fraud",
        "feeds": [],
        "google_news_queries": [
            "Quantexa AI analytics fraud AML platform",
            "Quantexa entity resolution decision intelligence",
        ],
    },
]

# ── Used once for baseline generation ────────────────────────────────────────
BASELINE_SYSTEM = """You are a senior competitive intelligence strategist at SAS.

Generate complete baseline battlecards for SAS Intelligent Decisioning competitors.

SAS Intelligent Decisioning:
- Native SAS Viya integration: enterprise ML, statistical models, Python/R
- Agentic AI with human-in-the-loop; fully traceable actions
- Trustworthy AI: LIME/SHAP explainability, model lineage, audit trails
- End-to-end lifecycle: dev to test to prod, governance, approval workflows
- Industries: fraud, customer engagement, manufacturing, public sector
- Strengths: governance, explainability, regulated industry trust, enterprise scale
- Gaps: no native knowledge graph (vs Quantexa); less fintech-native than Provenir/CRIF

Return ONLY valid JSON. No markdown, no preamble.

Schema (return ONLY the competitors for the names listed in the prompt):
{
  "competitors": [
    {
      "name": "<exact name>",
      "segment": "<market segment>",
      "threat_level": "<high | medium | low>",
      "battlecard": {
        "tab1_approach_to_market": {
          "market_strategy": "<1 sentence>",
          "customers": "<key segments and notable wins>",
          "verticals_served": "<industries targeted>",
          "partners": "<key partners>"
        },
        "tab2_top_3_things_to_know": [
          "<fact 1 for sales rep>",
          "<fact 2 for sales rep>",
          "<fact 3 for sales rep>"
        ],
        "tab3_product_claims": {
          "overview": "<2 sentences max>",
          "key_claims": ["<claim 1>", "<claim 2>"],
          "pricing_model": "<if known, else null>"
        },
        "tab4_strengths_weaknesses": {
          "strengths": ["<vs SAS ID>"],
          "weaknesses": ["<vs SAS ID>"],
          "differentiators": "<1 sentence>"
        },
        "tab5_sales_strategies": {
          "what_to_attack": "<where SAS wins>",
          "what_to_defend": "<where they attack SAS>",
          "trap_questions": ["<question 1>", "<question 2>"]
        }
      }
    }
  ]
}

Keep every field to the minimum needed. Sales reps read this between calls.
"""

# ── Used weekly for delta runs ────────────────────────────────────────────────
DELTA_SYSTEM = """You are a senior competitive intelligence strategist at SAS focused on SAS Intelligent Decisioning.

SAS Intelligent Decisioning strengths: governance, explainability, regulated industry trust, enterprise scale, native Viya integration, traceable agentic AI.
SAS gaps: no native knowledge graph (vs Quantexa); less fintech-native than Provenir/CRIF.

You will receive new RSS articles from competitors. Analyze ONLY what is new or changed.
Do not re-summarize stable known facts.

Return ONLY valid JSON for the competitors listed. No markdown, no preamble.

Schema:
{
  "market_signals": ["<cross-competitor trend, max 10 words>"],
  "competitors": [
    {
      "name": "<exact name>",
      "segment": "<segment>",
      "threat_level": "<high | medium | low>",
      "has_updates": true,
      "content_activity": {
        "blog_count": 0,
        "newsroom_count": 0,
        "trade_press_count": 0
      },
      "changes": {
        "market_approach_changed": false,
        "product_claims_changed": false,
        "what_changed": "<1-2 sentences on what is new, or null if nothing>"
      },
      "tab2_top_3_things_to_know": [
        "<updated fact 1>",
        "<updated fact 2>",
        "<updated fact 3>"
      ],
      "new_product_claims": ["<new claim if any>"],
      "sales_impact": {
        "what_to_attack": "<1 sentence — where SAS wins against them now>",
        "what_to_defend": "<1 sentence — what to be ready for>",
        "trap_question": "<1 question that reveals their weakness>"
      },
      "blog_suggestion": {
        "title": "<post title — do NOT name the competitor>",
        "angle": "<1 sentence argument SAS makes>",
        "why_now": "<1 sentence on timeliness>"
      }
    }
  ]
}

Rules:
- Only include competitors whose names appear in the prompt.
- Set has_updates: false and what_changed: null if no new articles found.
- blog_suggestion: include only if has_updates is true, otherwise omit.
- Market signals: 3-4 max, cross-competitor patterns only.
- Every field: 1 sentence maximum. Brevity is required.
"""
