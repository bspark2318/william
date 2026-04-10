import { Issue, IssueListItem } from "./types";

export const MOCK_ISSUES: IssueListItem[] = [
  { id: 1, week_of: "2026-04-07", title: "The Rise of Reasoning Models", edition: 2 },
  { id: 2, week_of: "2026-03-31", title: "Open Source Strikes Back", edition: 1 },
];

export const MOCK_ISSUE: Issue = {
  id: 1,
  week_of: "2026-04-07",
  title: "The Rise of Reasoning Models",
  edition: 2,
  featured_video: null,
  featured_videos: [
    {
      id: 1,
      title: "Inside Claude 4.6: What Changed and Why It Matters",
      video_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      thumbnail_url: "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=640&q=80",
      description:
        "A deep dive into the latest Anthropic model, its reasoning capabilities, and what it means for the industry.",
    },
    {
      id: 2,
      title: "The Open Source AI Race: Llama 5 vs. Mixtral",
      video_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      thumbnail_url: "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=640&q=80",
      description:
        "Comparing the two most capable open-weight models and what they mean for enterprise adoption.",
    },
    {
      id: 3,
      title: "AI Agents in Production: Lessons from the Field",
      video_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      thumbnail_url: "https://images.unsplash.com/photo-1531746790095-e5e1ef4aeb6e?w=640&q=80",
      description:
        "Practical insights on deploying autonomous agents at scale, from latency budgets to guardrails.",
    },
  ],
  stories: [
    {
      id: 1,
      title: "OpenAI Unveils GPT-5 with Native Multimodal Reasoning",
      summary:
        "Native multimodal reasoning across text, images, audio. Stronger scientific and coding benchmarks vs prior GPT.",
      bullet_points: [
        "Multimodal reasoning: text, images, audio in one stack.",
        "Notable lift on scientific problem-solving benchmarks.",
        "Code generation scores up vs GPT-4 class models.",
      ],
      source: "The Verge",
      url: "https://theverge.com",
      image_url: "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=300&q=80",
      date: "2026-04-07",
      tags: ["GPT-5", "Multimodal", "OpenAI"],
      display_order: 1,
    },
    {
      id: 2,
      title: "Google DeepMind Achieves Breakthrough in Protein Folding Speed",
      summary:
        "AlphaFold 4: millisecond structure prediction. Pharma racing on real-time discovery sims.",
      bullet_points: [
        "Structure predictions in milliseconds, not minutes.",
        "Enables real-time drug-discovery simulation loops.",
        "Heavy pharma interest in integration timelines.",
      ],
      source: "Nature",
      url: "https://nature.com",
      date: "2026-04-06",
      tags: ["DeepMind", "Biology", "AlphaFold"],
      display_order: 2,
    },
    {
      id: 3,
      title: "EU Passes Landmark AI Liability Directive",
      summary:
        "EU: deployers liable for AI harm. Compensation framework + high-risk transparency rules.",
      bullet_points: [
        "Strict liability for damages from deployed AI systems.",
        "Compensation framework spelled out for victims.",
        "High-risk apps face tighter transparency mandates.",
      ],
      source: "Reuters",
      url: "https://reuters.com",
      image_url: "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=300&q=80",
      date: "2026-04-05",
      tags: ["Regulation", "EU", "Policy"],
      display_order: 3,
    },
    {
      id: 4,
      title: "Meta Releases Llama 5 Under Apache 2.0 License",
      summary:
        "Llama 5 Apache 2.0 — Meta’s strongest open drop yet. Benchmarks near proprietary on reasoning/code.",
      bullet_points: [
        "Apache 2.0; Meta’s most capable open release so far.",
        "Reasoning benchmarks competitive with closed models.",
        "Code tasks within striking distance of proprietary stacks.",
      ],
      source: "TechCrunch",
      url: "https://techcrunch.com",
      date: "2026-04-04",
      tags: ["Meta", "Open Source", "Llama"],
      display_order: 4,
    },
    {
      id: 5,
      title: "AI Agents Now Handle 40% of Customer Service at Major Banks",
      summary:
        "McKinsey: ~40% of bank customer service now agent-driven. Inquiries through fraud, thin human oversight.",
      bullet_points: [
        "McKinsey: agents cover ~40% of bank customer-service volume.",
        "Scope runs account questions through fraud workflows.",
        "Minimal human oversight at scale in tier-1 banks.",
      ],
      source: "Financial Times",
      url: "https://ft.com",
      date: "2026-04-03",
      tags: ["Agents", "Finance", "Enterprise"],
      display_order: 5,
    },
  ],
};
