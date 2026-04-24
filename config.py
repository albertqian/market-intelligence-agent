"""
config.py — Competitor configuration and Claude system prompt.

Feed strategy (in priority order per competitor):
  1. Direct blog RSS — highest signal, lowest noise
  2. Newsroom / press RSS — product and partnership announcements
  3. Google News RSS — catches trade press and analyst coverage

Edit COMPETITORS freely to add, remove, or re-tune any entry.
"""

# Browser-like user agent — prevents 403s from corporate blog servers
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
            "https://www.sapiens.com/blog/feed/",
            "https://www.sapiens.com/news/feed/",
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
            "https://medium.com/feed/palantir",
            "https://blog.palantir.com/feed",
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
            "https://www.pega.com/blog/rss.xml",
            "https://www.pega.com/newsroom/press-releases/rss.xml",
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
            "https://www.ibm.com/blog/feed/",
            "https://research.ibm.com/blog/feed",
            "https://newsroom.ibm.com/rss/news-releases.htm",
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
            "https://www.fico.com/blogs/rss.xml",
            "https://www.fico.com/en/newsroom/rss.xml",
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
            "https://www.provenir.com/blog/feed/",
            "https://www.provenir.com/news/feed/",
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
            "https://www.actico.com/en/blog/feed/",
            "https://www.actico.com/blog/feed/",
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
            "https://www.crif.com/news/feed/",
            "https://www.crif.com/blog/feed/",
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
            "https://www.aeratechnology.com/blog/feed/",
            "https://www.aeratechnology.com/news/feed/",
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
            "https://www.quantexa.com/blog/feed/",
            "https://www.quantexa.com/news/feed/",
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

You will receive RSS feed articles from these competitors. Analyze what is strategically significant and return ONLY a valid JSON object. No markdown fences, no preamble, no commentary.

JSON schema:
{
  "generated_at": "<ISO 8601 timestamp>",
  "competitors": [
    {
      "name": "<exact name from the list above>",
      "threat_level": "<high | medium | low>",
      "headline": "<most significant recent development, max 12 words>",
      "developments": [
        {
          "title": "<short title>",
          "date": "<e.g. April 2025 or Q1 2025>",
          "summary": "<2-3 factual sentences based on the articles>",
          "sas_impact": "<specific implication for SAS Intelligent Decisioning, 1-2 sentences>"
        }
      ],
      "strategic_posture": "<one sentence on their current strategic direction>"
    }
  ],
  "recommendations": [
    {
      "priority": "<critical | high | medium>",
      "area": "<capability area, e.g. AI Agent Governance>",
      "action": "<specific, actionable step for the SAS product team>",
      "rationale": "<grounded in specific competitive data found, 1-2 sentences>"
    }
  ],
  "market_signals": [
    "<cross-competitor trend observation, max 12 words>"
  ]
}

Rules:
- Include ALL 10 competitors. If no articles were found, still include them with threat_level low and note the data gap.
- Provide 4-6 recommendations sorted by priority (critical first).
- Provide 4-6 market signals drawn from patterns across multiple competitors.
- Only flag developments that are genuinely new. Ignore evergreen marketing copy.
- Be direct and specific. Vague observations are not useful.
"""
