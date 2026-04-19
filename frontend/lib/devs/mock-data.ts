import { DevPost } from "./types";

export const MOCK_DEV_POSTS: DevPost[] = [
  {
    id: 1,
    source: "x",
    display_order: 1,
    topic: "evals",
    bullets: [
      {
        text: "Eval-first workflow is the new prompt engineering — top builders say most of their \"prompting\" work is now writing and iterating on evals before they touch a prompt.",
        sources: [
          {
            url: "https://x.com/karpathy/status/1",
            author_handle: "karpathy",
            author_name: "Andrej Karpathy",
          },
          {
            url: "https://x.com/HamelHusain/status/10",
            author_handle: "HamelHusain",
            author_name: "Hamel Husain",
          },
        ],
      },
      {
        text: "LLM-as-judge is gaining trust for regression gates — but only if you calibrate the judge against human labels first. Loud warnings this week about skipping that step.",
        sources: [
          {
            url: "https://x.com/eugeneyan/status/3",
            author_handle: "eugeneyan",
          },
          {
            url: "https://x.com/jxnlco/status/4",
            author_handle: "jxnlco",
            author_name: "Jason Liu",
          },
        ],
      },
      {
        text: "Recurring ask: faster eval iteration tooling. \"pytest for LLMs\" is the mental model people keep reaching for.",
        sources: [
          {
            url: "https://x.com/simonw/status/5",
            author_handle: "simonw",
            author_name: "Simon Willison",
          },
        ],
      },
    ],
  },
  {
    id: 2,
    source: "x",
    display_order: 2,
    topic: "agents",
    bullets: [
      {
        text: "The winning agent shape this week is narrow + deep: one task, tight eval loop, short context. Broad \"do everything\" agents keep underperforming on real work.",
        sources: [
          {
            url: "https://x.com/karpathy/status/20",
            author_handle: "karpathy",
            author_name: "Andrej Karpathy",
          },
          {
            url: "https://x.com/swyx/status/21",
            author_handle: "swyx",
          },
        ],
      },
      {
        text: "Sub-agent isolation (each sub-agent gets its own context + tools) is becoming the default pattern for anything longer than a few steps.",
        sources: [
          {
            url: "https://x.com/AnthropicAI/status/22",
            author_handle: "AnthropicAI",
          },
          {
            url: "https://x.com/jxnlco/status/23",
            author_handle: "jxnlco",
            author_name: "Jason Liu",
          },
        ],
      },
    ],
  },
  {
    id: 3,
    source: "x",
    display_order: 3,
    topic: "claude-code",
    bullets: [
      {
        text: "Constraint-driven prompting is outperforming instruction-heavy prompts: a failing test + a CLAUDE.md that forbids touching files outside the target is doing more than any verbose system prompt.",
        sources: [
          {
            url: "https://x.com/simonw/status/30",
            author_handle: "simonw",
            author_name: "Simon Willison",
          },
        ],
      },
      {
        text: "Heavy usage of skills + sub-agents to keep the main context clean — people are treating context window like a hot loop, not a scratchpad.",
        sources: [
          {
            url: "https://x.com/swyx/status/31",
            author_handle: "swyx",
          },
          {
            url: "https://x.com/HamelHusain/status/32",
            author_handle: "HamelHusain",
            author_name: "Hamel Husain",
          },
        ],
      },
    ],
  },
  {
    id: 4,
    source: "hn",
    url: "https://hamel.dev/blog/posts/evals/",
    hn_url: "https://news.ycombinator.com/item?id=9999001",
    published_at: "2026-04-17",
    display_order: 4,
    title: "A field guide to rapidly improving LLM apps (Hamel Husain)",
    points: 843,
    comments: 214,
    bullets: [
      "Commenters back the \"look at 100 traces before prompting\" advice — several report cutting failure rates in half from error analysis alone.",
      "Debate on whether LLM-as-judge is trustworthy enough for regression gates; most say yes if you calibrate against human labels first.",
      "Recurring ask: tooling for cheap, fast eval iteration — pytest-for-LLMs is the analogy.",
    ],
    topics: ["evals", "practices"],
  },
  {
    id: 5,
    source: "hn",
    url: "https://github.com/example/show-hn-tool",
    hn_url: "https://news.ycombinator.com/item?id=9999002",
    published_at: "2026-04-16",
    display_order: 5,
    title: "Show HN: Trace — drop-in OTel tracing for any LLM SDK",
    points: 512,
    comments: 97,
    bullets: [
      "Span schema aligns with OpenInference — drop-in for teams already on OTel collectors.",
      "Main pushback: adds ~8ms latency per call; author says they're working on a sampling mode.",
      "Several commenters ask for LangGraph and CrewAI adapters next.",
    ],
    topics: ["tooling", "observability"],
  },
  {
    id: 6,
    source: "hn",
    url: "https://engineering.example.com/we-replaced-langchain",
    hn_url: "https://news.ycombinator.com/item?id=9999003",
    published_at: "2026-04-15",
    display_order: 6,
    title: "We replaced LangChain with 300 lines of Python",
    points: 1204,
    comments: 389,
    bullets: [
      "Team reports latency dropped 40% and the team's mental model of the system improved more than they expected — abstractions were hiding behavior.",
      "Recurring comment: most orgs don't need a framework, they need a retry/backoff helper and a well-typed tool-call loop.",
      "Counter-take: frameworks earn their keep once you have 10+ integrations and a non-trivial eval surface — don't roll your own past that point.",
    ],
    topics: ["frameworks", "practices"],
  },
  {
    id: 7,
    source: "github",
    url: "https://github.com/anthropics/claude-agent-sdk",
    repo: "anthropics/claude-agent-sdk",
    title: "claude-agent-sdk v0.8.0",
    version: "v0.8.0",
    why_it_matters:
      "Sub-agent isolation is the pattern most teams are converging on for long-running agents — this lands it as a first-class primitive.",
    release_bullets: [
      "New sub-agent isolation: each sub-agent gets its own context, tools, and memory.",
      "`memory` primitive for long-running runs — persistent scratchpad across turns.",
      "Breaking: `run()` now returns an async iterator instead of a Promise. Migration is mechanical but touches every call site.",
    ],
    has_breaking_changes: true,
    stars: 14820,
    stars_velocity_7d: 612,
    published_at: "2026-04-16",
    display_order: 7,
    topics: ["agents", "sdk"],
  },
  {
    id: 8,
    source: "github",
    url: "https://github.com/vllm-project/vllm",
    repo: "vllm-project/vllm",
    title: "vLLM v0.8.2 — speculative decoding on by default",
    version: "v0.8.2",
    why_it_matters:
      "Free throughput win if you self-host — no code changes, just upgrade and measure.",
    release_bullets: [
      "Auto-selects a speculator per model from the HF config — zero-config for most setups.",
      "Up to 2.3x throughput on Llama-5-70B in benchmarks.",
      "Fixes a long-standing OOM on 8-bit quant paths under high concurrency.",
    ],
    has_breaking_changes: false,
    stars: 42100,
    stars_velocity_7d: 890,
    published_at: "2026-04-15",
    display_order: 8,
    topics: ["inference", "vllm"],
  },
  {
    id: 9,
    source: "github",
    url: "https://github.com/modelcontextprotocol/servers",
    repo: "modelcontextprotocol/servers",
    title: "MCP reference servers — v1.3",
    version: "v1.3",
    why_it_matters:
      "MCP auth is now stable — means production MCP servers are no longer gated on spec churn.",
    release_bullets: [
      "New Postgres, BigQuery, and Linear reference servers.",
      "Auth spec finalized; bearer-token flow is stable and backward-compatible.",
      "Improved error surfaces — clients now get structured error codes instead of string blobs.",
    ],
    has_breaking_changes: false,
    stars: 9840,
    stars_velocity_7d: 412,
    published_at: "2026-04-14",
    display_order: 9,
    topics: ["mcp", "tooling"],
  },
];
