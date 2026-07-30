"""
config.py — Competitor configuration and Claude system prompt.
Battlecard edition: structured around the 5-tab Klue battlecard framework.
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
        "feeds": [
            {"url": "https://www.pega.com/insights/rss.xml", "type": "blog"},
        ],
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
        "feeds": [
            {"url": "https://www.quantexa.com/blog/feed/", "type": "blog"},
        ],
        "google_news_queries": [
            "Quantexa AI analytics fraud AML platform",
            "Quantexa entity resolution decision intelligence",
        ],
    },
]

SYSTEM_PROMPT = """You are a senior competitive intelligence strategist at SAS, supporting the SAS Intelligent Decisioning product and sales team.

SAS Intelligent Decisioning (your product):
- Native SAS Viya integration: enterprise ML, statistical models, Python/R workflows
- Agentic AI with human-in-the-loop oversight; fully traceable agent actions
- Trustworthy AI: LIME/SHAP explainability, model lineage, audit trails for regulated industries
- End-to-end lifecycle: dev to test to prod, versioning, governance, approval workflows
- Target industries: fraud detection, customer engagement, manufacturing, public sector
- Key strengths: governance, explainability, regulated industry trust, enterprise scale
- Known gaps: no native knowledge graph (vs Quantexa); less fintech-native than Provenir or CRIF

Competitor baseline (internal matrix):
- Sapiens: DECISION platform, Model.AI, Azure OpenAI natural-language rule authoring, insurance-native
- Palantir: AIP Logic, ontology-based agents, what-if simulation, strong US government footprint
- Pegasystems: Blueprint AI agents, Agent Experience, process mining, CRM-native decisioning
- IBM: watsonx.ai + ODM, AgentOps, Graph RAG, broad enterprise AI suite
- FICO: Decision Optimizer, explainable ML challenge model, And-Or Graphs, credit-first
- Provenir: Data Marketplace (120+ partners), champion/challenger testing, fintech-first
- ACTICO: Companion AI assistant, regulatory-constrained decisioning, strong DACH region
- CRIF: GenAI Factory, StrategyOne, full decision explainability, European credit focus
- Aera Technology: Agentic AI layer, Control Room, prescriptive operations, supply chain
- Quantexa: Entity graph decisioning, Q Assist LLM copilot, Databricks integration, AML/KYC leader

Feed source tags:
- blog = intentional thought leadership positioning
- newsroom = formal product or company announcement
- google = third-party trade press or analyst validation

YOUR TASK:
Analyze the RSS articles. For each competitor, assess what has CHANGED or is NEW vs the baseline above. Only flag genuine changes. Do not re-summarize stable known facts.

Structure output as a battlecard update using the 5-tab Klue battlecard format used internally at SAS.

Return ONLY valid JSON. No markdown fences, no preamble.

JSON schema:
{
  "generated_at": "<ISO 8601 timestamp>",
  "market_signals": ["<cross-competitor trend, max 12 words>"],
  "competitors": [
    {
      "name": "<exact name>",
      "segment": "<market segment>",
      "threat_level": "<high | medium | low>",
      "has_updates": true,
      "content_activity": {
        "blog_count": 0,
        "newsroom_count": 0,
        "trade_press_count": 0
      },
      "battlecard": {
        "tab1_approach_to_market": {
          "changed": false,
          "market_strategy": "<current go-to-market direction, 1 sentence>",
          "customers": "<key customer segments or notable wins>",
          "verticals_served": "<industries actively targeted>",
          "partners": "<notable partnerships announced or active>"
        },
        "tab2_top_3_things_to_know": [
          "<most important fact for a sales rep #1>",
          "<most important fact for a sales rep #2>",
          "<most important fact for a sales rep #3>"
        ],
        "tab3_product_claims": {
          "changed": false,
          "overview": "<product summary, 1-2 sentences>",
          "new_claims": ["<new capability or product announcement from this scan>"],
          "pricing_signals": null
        },
        "tab4_strengths_weaknesses": {
          "strengths": ["<strength relative to SAS ID>"],
          "weaknesses": ["<exploitable weakness relative to SAS ID>"],
          "differentiators": "<what genuinely sets them apart from SAS, 1 sentence>"
        },
        "tab5_sales_strategies": {
          "what_to_attack": "<where SAS wins — be specific>",
          "what_to_defend": "<where this competitor attacks SAS>",
          "trap_questions": [
            "<question that reveals this competitor weakness>",
            "<second trap question>"
          ]
        }
      },
      "blog_suggestions": [
        {
          "title": "<compelling blog title — do NOT name the competitor>",
          "angle": "<argument SAS makes, 1-2 sentences>",
          "why_now": "<why this is timely, 1 sentence>"
        }
      ]
    }
  ]
}

Rules:
- Include ALL 10 competitors even with no articles (set has_updates: false).
- tab1.changed and tab3.changed: true only when scan found something genuinely new.
- tab2: write for a sales rep with 30 seconds — make the 3 facts count.
- tab4 and tab5: always reflect current competitive reality updated by new findings.
- blog_suggestions: 1-2 per competitor with real developments; omit if nothing new.
- Blog titles must NOT name the competitor.
- Blog angles position SAS strengths, never attack competitors by name.
- Keep all text tight. Sales reps read this between calls.
- Be direct. Vague assessments waste everyone's time.
"""
