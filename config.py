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
        "feeds": [
            {"url": "https://www.sapiens.com/feed/", "type": "blog"},
        ],
        "tavily_queries": [
            "Sapiens International decisioning AI product announcement",
            "Sapiens DECISION platform new release insurance",
        ],
    },
    {
        "name": "Palantir",
        "segment": "Government / Enterprise",
        "feeds": [
            {"url": "https://medium.com/feed/palantir", "type": "blog"},
        ],
        "tavily_queries": [
            "Palantir AIP platform product launch enterprise AI",
            "Palantir artificial intelligence decisioning announcement",
        ],
    },
    {
        "name": "Pegasystems",
        "segment": "CRM / BPM",
        "feeds": [
            {"url": "https://www.pega.com/about/news/rss.xml", "type": "newsroom"},
        ],
        "tavily_queries": [
            "Pegasystems Pega AI decisioning product launch 2026",
            "Pega decisioning automation new feature release",
        ],
    },
    {
        "name": "IBM",
        "segment": "Enterprise AI",
        "feeds": [
            {"url": "https://www.ibm.com/blog/feed/", "type": "blog"},
        ],
        "tavily_queries": [
            "IBM watsonx AI decisioning product announcement 2026",
            "IBM decision optimization ODM new release",
        ],
    },
    {
        "name": "FICO",
        "segment": "Credit / Risk",
        "feeds": [
            {"url": "https://www.fico.com/blogs/feed", "type": "blog"},
        ],
        "tavily_queries": [
            "FICO credit scoring AI platform product update 2026",
            "FICO decision management new announcement",
        ],
    },
    {
        "name": "Provenir",
        "segment": "Fintech",
        "feeds": [
            {"url": "https://www.provenir.com/feed/", "type": "blog"},
        ],
        "tavily_queries": [
            "Provenir fintech credit risk AI decisioning 2026",
            "Provenir platform new product feature announcement",
        ],
    },
    {
        "name": "ACTICO",
        "segment": "Compliance / Reg-Tech",
        "feeds": [
            {"url": "https://www.actico.com/feed/", "type": "blog"},
        ],
        "tavily_queries": [
            "ACTICO decision management compliance AI 2026",
            "ACTICO rules engine software new release",
        ],
    },
    {
        "name": "CRIF",
        "segment": "Credit Risk",
        "feeds": [],
        "tavily_queries": [
            "CRIF credit risk AI analytics platform announcement 2026",
            "CRIF decisioning GenAI product update",
        ],
    },
    {
        "name": "Aera Technology",
        "segment": "Supply Chain / Ops",
        "feeds": [],
        "tavily_queries": [
            "Aera Technology agentic AI supply chain decisioning 2026",
            "Aera Technology decision automation new product",
        ],
    },
    {
        "name": "Quantexa",
        "segment": "AML / KYC / Fraud",
        "feeds": [
            {"url": "https://www.quantexa.com/blog/feed/", "type": "blog"},
        ],
        "tavily_queries": [
            "Quantexa AI analytics fraud AML platform announcement 2026",
            "Quantexa entity resolution decision intelligence new release",
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

SAS Intelligent Decisioning strengths: governance, explainability, regulated industry trust,
enterprise scale, native Viya integration, traceable agentic AI, human-in-the-loop controls.
SAS gaps: no native knowledge graph (vs Quantexa); less fintech-native than Provenir/CRIF.

You will receive new articles and press coverage from competitors. Your job is to answer
three specific questions for the SAS product and marketing teams:

QUESTION 1 — INTEL: What does SAS need to know about what competitors did this week?
Focus on product launches, partnerships, customer wins, analyst recognition, and positioning shifts.
Only include what is genuinely new. Do not summarize stable known facts.

QUESTION 2 — PRODUCT: What should SAS do from a product standpoint in response?
Be specific: feature gaps to close, positioning adjustments, roadmap signals, capabilities
to accelerate. Frame this as concrete recommendations, not observations.

QUESTION 3 — MARKETING: What can SAS say from a marketing and content standpoint?
Suggest specific blog posts, thought leadership angles, or messaging moves that address
competitor activity without naming competitors directly. Each suggestion should be
publishable and timely.

Return ONLY valid JSON for the competitors listed. No markdown, no preamble.

Schema:
{
  "weekly_brief": {
    "intel_summary": [
      "<key thing SAS needs to know — 1 sentence, specific and factual>"
    ],
    "product_actions": [
      "<specific product recommendation for SAS ID team — 1 sentence, actionable>"
    ],
    "marketing_plays": [
      {
        "title": "<blog or content title — do NOT name the competitor>",
        "angle": "<the argument SAS makes in 1 sentence>",
        "why_now": "<why this is timely given this week's competitive activity>"
      }
    ]
  },
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
      }
    }
  ]
}

Rules:
- Only include competitors whose names appear in the prompt.
- Set has_updates: false and what_changed: null if no new articles found.
- weekly_brief should synthesize across ALL competitors, not just those with updates.
- intel_summary: 3-5 bullets maximum. Cross-competitor patterns preferred over single events.
- product_actions: 2-4 concrete recommendations maximum.
- marketing_plays: 2-3 content ideas maximum, each tied to something specific that happened.
- Every field: 1 sentence maximum. Brevity is required.
"""
