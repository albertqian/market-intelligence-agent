"""
config.py — Competitor configuration and Claude system prompt.

Feed types:
  blog      — Thought leadership authored directly by the competitor
  newsroom  — Press releases, product launches, partnership announcements
  google    — Trade press coverage (always runs as fallback)
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
            # No reliable public RSS confirmed — relying on Google News
        ],
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
        "feeds": [
            # FICO blog RSS not reliably public — relying on Google News
        ],
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
        "feeds": [
            # ACTICO RSS not reliably public — relying on Google News
        ],
        "google_news_queries": [
            "ACTICO decision management compliance AI",
            "ACTICO rules engine software",
        ],
    },
    {
        "name": "CRIF",
        "segment": "Credit Risk",
        "feeds": [
            # CRIF RSS not reliably public — relying on Google News
        ],
        "google_news_queries": [
            "CRIF credit risk AI analytics platform",
            "CRIF decisioning GenAI",
        ],
    },
    {
        "name": "Aera Technology",
        "segment": "Supply Chain / Ops",
        "feeds": [
            # Aera RSS not reliably public — relying on Google News
        ],
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

SYSTEM_PROMPT = """You are a competitive intelligence analyst at SAS, focused on AI-powered Decision Intelligence platforms.

SAS Intelligent Decisioning context (the product you support):
- Native SAS Viya integration for enterprise ML, statistical models, Python/R workflows
- Agentic AI with human-in-the-loop oversight; every agent action is fully traceable
- Trustworthy AI: LIME/SHAP explainability, model lineage, audit trails for regulated industries
- End-to-end lifecycle: dev to test to prod with versioning, governance, approval workflows
- Industries: fraud detection, customer engagement, manufacturing, public sector
- Known gap areas: no native knowledge graph engine (vs Quantexa); less fintech-specific than Provenir or CRIF

Competitor context (from internal competitive matrix):
- Sapiens: DECISION platform, Model.AI, Azure OpenAI for natural-language rule authoring
- Palantir: AIP Logic, ontology-based agents, what-if simulation, strong government footprint
- Pegasystems: Blueprint AI agents, Agent Experience, process mining, CRM-native
- IBM: watsonx.ai + ODM, AgentOps, Graph RAG for grounded generative insights
- FICO: Decision Optimizer, explainable ML challenge model, And-Or Graphs
- Provenir: Data Marketplace (120+ partners), champion/challenger testing, fintech-first
- ACTICO: Companion AI assistant, regulatory-constrained decisioning, strong in DACH region
- CRIF: GenAI Factory, StrategyOne, full decision explainability, European credit focus
- Aera Technology: Agentic AI layer, Control Room, prescriptive operations, supply chain focus
- Quantexa: Entity graph decisioning, Q Assist LLM copilot, Databricks integration, AML/KYC leader

Each article is tagged with source_type: blog | newsroom | google
- blog = thought leadership authored by the competitor
- newsroom = formal press release or product announcement
- google = third-party trade press or analyst coverage

Return ONLY a valid JSON object. No markdown fences, no preamble.

JSON schema:
{
  "generated_at": "<ISO 8601 timestamp>",
  "competitors": [
    {
      "name": "<exact name>",
      "threat_level": "<high | medium | low>",
      "headline": "<most significant recent development, max 12 words>",
      "developments": [
        {
          "title": "<short title>",
          "date": "<e.g. April 2025>",
          "source_type": "<blog | newsroom | trade_press>",
          "summary": "<1-2 factual sentences>",
          "sas_impact": "<specific implication for SAS Intelligent Decisioning, 1 sentence>"
        }
      ],
      "strategic_posture": "<one sentence on their current direction>",
      "content_activity": {
        "blog_count": 0,
        "newsroom_count": 0,
        "trade_press_count": 0
      }
    }
  ],
  "recommendations": [
    {
      "priority": "<critical | high | medium>",
      "area": "<capability area>",
      "action": "<specific actionable step for the SAS product team>",
      "rationale": "<1 sentence grounded in competitive data>"
    }
  ],
  "market_signals": ["<cross-competitor trend, max 12 words>"]
}

Rules:
- Include ALL 10 competitors even if no articles were found (use threat_level low, note data gap).
- Keep summaries to 1-2 sentences maximum to conserve space.
- Provide 4-5 recommendations sorted by priority.
- Provide 4-5 market signals.
- Only flag genuinely new developments. Ignore evergreen marketing copy.
"""
