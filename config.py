"""
config.py — Competitor configuration and Claude system prompt.

Feed types:
  blog      — Thought leadership, opinion, technical content authored by the competitor
  newsroom  — Press releases, product launches, partnership announcements
  google    — Trade press coverage, analyst mentions, third-party reporting

Edit COMPETITORS freely to add, remove, or re-tune any entry.
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
            {"url": "https://www.sapiens.com/blog/feed/",  "type": "blog"},
            {"url": "https://www.sapiens.com/news/feed/",  "type": "newsroom"},
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
            {"url": "https://medium.com/feed/palantir",    "type": "blog"},
            {"url": "https://blog.palantir.com/feed",      "type": "blog"},
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
            {"url": "https://www.pega.com/blog/rss.xml",                        "type": "blog"},
            {"url": "https://www.pega.com/newsroom/press-releases/rss.xml",     "type": "newsroom"},
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
            {"url": "https://www.ibm.com/blog/feed/",                   "type": "blog"},
            {"url": "https://research.ibm.com/blog/feed",               "type": "blog"},
            {"url": "https://newsroom.ibm.com/rss/news-releases.htm",   "type": "newsroom"},
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
            {"url": "https://www.fico.com/blogs/rss.xml",           "type": "blog"},
            {"url": "https://www.fico.com/en/newsroom/rss.xml",     "type": "newsroom"},
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
            {"url": "https://www.provenir.com/blog/feed/",  "type": "blog"},
            {"url": "https://www.provenir.com/news/feed/",  "type": "newsroom"},
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
            {"url": "https://www.actico.com/en/blog/feed/", "type": "blog"},
            {"url": "https://www.actico.com/blog/feed/",    "type": "blog"},
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
            {"url": "https://www.crif.com/news/feed/",  "type": "newsroom"},
            {"url": "https://www.crif.com/blog/feed/",  "type": "blog"},
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
            {"url": "https://www.aeratechnology.com/blog/feed/", "type": "blog"},
            {"url": "https://www.aeratechnology.com/news/feed/", "type": "newsroom"},
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
            {"url": "https://www.quantexa.com/news/feed/", "type": "newsroom"},
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

Each article in the feed is tagged with a source_type:
- blog      = thought leadership authored directly by the competitor
- newsroom  = formal press release or product announcement
- google    = third-party trade press or analyst coverage

Use source_type to inform your analysis. A blog post signals intentional positioning. A press release signals a formal commitment. Trade press signals market validation.

You will receive RSS feed articles from these competitors. Return ONLY a valid JSON object. No markdown fences, no preamble.

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
          "summary": "<2-3 factual sentences>",
          "sas_impact": "<specific implication for SAS Intelligent Decisioning>"
        }
      ],
      "strategic_posture": "<one sentence on their current direction>",
      "content_activity": {
        "blog_count": <int>,
        "newsroom_count": <int>,
        "trade_press_count": <int>
      }
    }
  ],
  "recommendations": [
    {
      "priority": "<critical | high | medium>",
      "area": "<capability area>",
      "action": "<specific, actionable step for the SAS product team>",
      "rationale": "<grounded in competitive data, 1-2 sentences>"
    }
  ],
  "market_signals": [
    "<cross-competitor trend observation, max 12 words>"
  ]
}

Rules:
- Include ALL 10 competitors even if no articles were found.
- Provide 4-6 recommendations sorted by priority.
- Provide 4-6 market signals.
- Only flag genuinely new developments. Ignore evergreen marketing copy.
- Be direct. Vague observations are not useful.
"""
