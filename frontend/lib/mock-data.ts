import { Issue, IssueListItem } from "./types";

export const MOCK_ISSUES: IssueListItem[] = [
  { id: 1, week_of: "2026-04-07", title: "The Rise of Reasoning Models" },
  { id: 2, week_of: "2026-03-31", title: "Open Source Strikes Back" },
];

export const MOCK_ISSUE: Issue = {
  id: 1,
  week_of: "2026-04-07",
  title: "The Rise of Reasoning Models",
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
        "The latest model from OpenAI demonstrates unprecedented ability to reason across text, images, and audio simultaneously. Researchers report significant improvements in scientific problem-solving and code generation tasks.",
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
        "AlphaFold 4 can now predict protein structures in milliseconds rather than minutes, opening the door to real-time drug discovery simulations. The pharmaceutical industry is already racing to integrate the technology.",
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
        "Companies deploying AI systems in the European Union will now face strict liability for damages caused by their models. The directive establishes a framework for compensation and mandates transparency in high-risk applications.",
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
        "In a bold move for open source AI, Meta has released its most capable model yet with a fully permissive license. Early benchmarks show it competing with proprietary models on reasoning and code tasks.",
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
        "A new report from McKinsey reveals that autonomous AI agents have reached a tipping point in financial services, handling everything from account inquiries to fraud detection with minimal human oversight.",
      source: "Financial Times",
      url: "https://ft.com",
      date: "2026-04-03",
      tags: ["Agents", "Finance", "Enterprise"],
      display_order: 5,
    },
  ],
};
