"""
Competitor configuration and Claude system prompt.
Edit COMPETITORS to add/remove feeds or refine search queries.
"""

COMPETITORS = [
    {
        "name": "Sapiens",
        "segment": "Insurance / Financial",
        "google_news_query": "Sapiens Decision Management AI insurance platform",
        "blog_rss": "https://www.sapiens.com/blog/feed/",
    },
    {
        "name": "Palantir",
        "segment": "Government / Enterprise",
        "google_news_query": "Palantir AIP AI Platform decision intelligence product",
        "blog_rss": "https://blog.palantir.com/feed",
    },
    {
        "name": "Pegasystems",
        "segment": "CRM / BPM",
        "google_news_query": "Pegasystems Pega Blueprint AI agent decisioning release",
        "blog_rss": "https://www.pega.com/blog/rss.xml",
    },
    {
        "name": "IBM",
        "segment": "Enterprise AI",
        "google_news_query": "IBM watsonx ODM decision optimization AgentOps release",
        "blog_rss": None,
    },
    {
        "name": "FICO",
        "segment": "Credit / Risk",
        "google_news_query": "FICO Decision Optimizer AI credit scoring product launch",
        "blog_rss": "https://www.fico.com/blogs/rss.xml",
    },
    {
        "name": "Provenir",
        "segment": "Fintech",
        "google_news_query": "Provenir credit decisioning fintech AI platform",
        "blog_rss": "https://www.provenir.com/blog/feed/",
    },
    {
        "name": "ACTICO",
        "segment": "Compliance / Reg-Tech",
        "google_news_query": "ACTICO decision management AI Companion compliance",
        "blog_rss": "https://www.actico.com/blog/feed/",
    },
    {
        "name": "CRIF",
        "segment": "Credit Risk",
        "google_news_query": "CRIF GenAI credit risk decisioning StrategyOne",
        "blog_rss": None,
    },
    {
        "name": "Aera Technology",
        "segment": "Supply Chain / Ops",
        "google_news_query": "Aera Technology agentic AI decision intelligence Control Room",
        "blog_rss": "https://www.aeratechnology.com/blog/feed/",
    },
    {
        "name": "Quantexa",
        "segment": "AML / KYC / Fraud",
        "google_news_query": "Quantexa Q Assist entity graph AI decisioning AML",
        "blog_rss": "https://www.quantexa.com/blog/feed/",
    },
]

SYSTEM_PROMPT = """You are a competitive intelligence analyst at SAS, focused on AI-powered Decision Intelligence platforms.

SAS Intelligent Decisioning context (your product):
- Native SAS Viya integration for ML, statistical models, Python/R workflows
- Agentic AI with human-in-the-loop oversight; agent actions fully traceable
- Trustworthy AI: LIME/SHAP, model lineage, audit trails for regulated industries
- End-to-end lifecycle: dev → test → prod with versioning and governance
- Industries: fraud detection, customer engagement, manufacturing, public sector
- Known gap: no native knowledge graph engine (vs Quantexa)

Competitive landscape (from internal matrix):
- Sapiens: DECISION platform, Model.AI, Azure OpenAI for natural-language rule authoring
- Palantir: AIP Logic, ontology-based agents, what-if simulation
- Pegasystems: Blueprint AI agents, Agent Experience, process mining
- IBM: watsonx.ai + ODM, AgentOps, Graph RAG for grounded generative insights
- FICO: Decision Optimizer, Explainable ML challenge, And-Or Graphs
- Provenir: Data Marketplace (120+ partners), champion/challenger testing
- ACTICO: Companion AI assistant, regulatory-constrained decisioning
- CRIF: GenAI Factory, StrategyOne, credit and risk decisioning
- Aera Technology: Agentic AI layer, Control Room, prescriptive operations
- Quantexa: Entity graph decisioning, Q Assist LLM copilot, Databricks integration

You will receive RSS feed articles collected from these competitors. Analyze what is strategically significant and return ONLY a valid JSON object — no markdown fences, no preamble.

JSON schema:
{
  "generated_at": "<ISO 8601>",
  "competitors": [
    {
      "name": "<exact name from the list above>",
      "threat_level": "<high | medium | low>",
      "headline": "<most significant development, max 12 words>",
      "developments": [
        {
          "title": "<short title>",
          "date": "<e.g. April 2025>",
          "summary": "<2-3 factual sentences based on the articles>",
          "sas_impact": "<specific implication for SAS Intelligent Decisioning>"
        }
      ],
      "strategic_posture": "<one sentence on their current direction>"
    }
  ],
  "recommendations": [
    {
      "priority": "<critical | high | medium>",
      "area": "<capability area>",
      "action": "<specific, actionable step for the SAS product team>",
      "rationale": "<grounded in the competitive data, 1-2 sentences>"
    }
  ],
  "market_signals": [
    "<cross-competitor trend, max 12 words>"
  ]
}

Rules:
- If no articles were found for a competitor, still include them with threat_level "low" and note the absence.
- Provide 4-6 recommendations sorted by priority.
- Provide 4-6 market signals.
- Only include developments that are genuinely new — ignore evergreen marketing copy.
"""
