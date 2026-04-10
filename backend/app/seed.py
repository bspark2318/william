"""Seed the database with mock data mirroring frontend/lib/mock-data.ts."""

from .database import Base, SessionLocal, engine
from .models import FeaturedVideo, Issue, Story


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Issue).count() > 0:
        print("Database already seeded, skipping.")
        db.close()
        return

    issue1 = Issue(id=1, week_of="2026-04-07", title="The Rise of Reasoning Models")
    issue2 = Issue(id=2, week_of="2026-03-31", title="Open Source Strikes Back")
    db.add_all([issue1, issue2])
    db.flush()

    stories_issue1 = [
        Story(
            issue_id=1,
            title="OpenAI Unveils GPT-5 with Native Multimodal Reasoning",
            summary="Native multimodal reasoning across text, images, audio. Stronger scientific and coding benchmarks vs prior GPT.",
            bullet_points=[
                "Multimodal reasoning: text, images, audio in one stack.",
                "Notable lift on scientific problem-solving benchmarks.",
                "Code generation scores up vs GPT-4 class models.",
            ],
            source="The Verge",
            url="https://theverge.com",
            image_url="https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=300&q=80",
            date="2026-04-07",
            tags=["GPT-5", "Multimodal", "OpenAI"],
            display_order=1,
        ),
        Story(
            issue_id=1,
            title="Google DeepMind Achieves Breakthrough in Protein Folding Speed",
            summary="AlphaFold 4: millisecond structure prediction. Pharma racing on real-time discovery sims.",
            bullet_points=[
                "Structure predictions in milliseconds, not minutes.",
                "Enables real-time drug-discovery simulation loops.",
                "Heavy pharma interest in integration timelines.",
            ],
            source="Nature",
            url="https://nature.com",
            date="2026-04-06",
            tags=["DeepMind", "Biology", "AlphaFold"],
            display_order=2,
        ),
        Story(
            issue_id=1,
            title="EU Passes Landmark AI Liability Directive",
            summary="EU: deployers liable for AI harm. Compensation framework + high-risk transparency rules.",
            bullet_points=[
                "Strict liability for damages from deployed AI systems.",
                "Compensation framework spelled out for victims.",
                "High-risk apps face tighter transparency mandates.",
            ],
            source="Reuters",
            url="https://reuters.com",
            image_url="https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=300&q=80",
            date="2026-04-05",
            tags=["Regulation", "EU", "Policy"],
            display_order=3,
        ),
        Story(
            issue_id=1,
            title="Meta Releases Llama 5 Under Apache 2.0 License",
            summary="Llama 5 Apache 2.0 — Meta’s strongest open drop yet. Benchmarks near proprietary on reasoning/code.",
            bullet_points=[
                "Apache 2.0; Meta’s most capable open release so far.",
                "Reasoning benchmarks competitive with closed models.",
                "Code tasks within striking distance of proprietary stacks.",
            ],
            source="TechCrunch",
            url="https://techcrunch.com",
            date="2026-04-04",
            tags=["Meta", "Open Source", "Llama"],
            display_order=4,
        ),
        Story(
            issue_id=1,
            title="AI Agents Now Handle 40% of Customer Service at Major Banks",
            summary="McKinsey: ~40% of bank customer service now agent-driven. Inquiries through fraud, thin human oversight.",
            bullet_points=[
                "McKinsey: agents cover ~40% of bank customer-service volume.",
                "Scope runs account questions through fraud workflows.",
                "Minimal human oversight at scale in tier-1 banks.",
            ],
            source="Financial Times",
            url="https://ft.com",
            date="2026-04-03",
            tags=["Agents", "Finance", "Enterprise"],
            display_order=5,
        ),
    ]

    stories_issue2 = [
        Story(
            issue_id=2,
            title="Mistral AI Raises $1.3B at $13B Valuation",
            summary="Mistral: $1.3B raise, $13B post. Paris team scales inference and enterprise.",
            bullet_points=[
                "$1.3B round; ~$13B valuation.",
                "Capital aimed at inference capacity and enterprise GTM.",
            ],
            source="Bloomberg",
            url="https://bloomberg.com",
            date="2026-03-31",
            tags=["Mistral", "Funding"],
            display_order=1,
        ),
        Story(
            issue_id=2,
            title="Open Source LLMs Now Match GPT-4 on Key Benchmarks",
            summary="Open-weight models hit GPT-4 parity on selected leaderboards, per multi-lab eval.",
            bullet_points=[
                "Open models match GPT-4 on a defined benchmark slice.",
                "Result from multi-institution reproducibility effort.",
            ],
            source="Ars Technica",
            url="https://arstechnica.com",
            date="2026-03-30",
            tags=["Open Source", "Benchmarks"],
            display_order=2,
        ),
        Story(
            issue_id=2,
            title="NVIDIA Announces Next-Gen AI Chip Architecture",
            summary="Blackwell Ultra: NVIDIA claims ~3× inference throughput vs prior gen at same power class.",
            bullet_points=[
                "Blackwell Ultra targets datacenter inference scale-outs.",
                "~3× throughput claim vs previous Blackwell-class parts.",
            ],
            source="Wired",
            url="https://wired.com",
            date="2026-03-29",
            tags=["NVIDIA", "Hardware"],
            display_order=3,
        ),
        Story(
            issue_id=2,
            title="AI-Generated Code Now Accounts for 25% of All New Code at Google",
            summary="Google internal: ~25% of new code lines AI-assisted; trend climbing QoQ.",
            bullet_points=[
                "~25% of new code attributed to AI assistance internally.",
                "Share still rising quarter over quarter.",
            ],
            source="The Information",
            url="https://theinformation.com",
            date="2026-03-28",
            tags=["Google", "Code Generation"],
            display_order=4,
        ),
    ]

    db.add_all(stories_issue1 + stories_issue2)

    videos_issue1 = [
        FeaturedVideo(
            issue_id=1,
            title="Inside Claude 4.6: What Changed and Why It Matters",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            thumbnail_url="https://images.unsplash.com/photo-1677442136019-21780ecad995?w=640&q=80",
            description="A deep dive into the latest Anthropic model, its reasoning capabilities, and what it means for the industry.",
        ),
        FeaturedVideo(
            issue_id=1,
            title="The Open Source AI Race: Llama 5 vs. Mixtral",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            thumbnail_url="https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=640&q=80",
            description="Comparing the two most capable open-weight models and what they mean for enterprise adoption.",
        ),
        FeaturedVideo(
            issue_id=1,
            title="AI Agents in Production: Lessons from the Field",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            thumbnail_url="https://images.unsplash.com/photo-1531746790095-e5e1ef4aeb6e?w=640&q=80",
            description="Practical insights on deploying autonomous agents at scale, from latency budgets to guardrails.",
        ),
    ]

    videos_issue2 = [
        FeaturedVideo(
            issue_id=2,
            title="Why Open Source AI Is Winning",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            thumbnail_url="https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=640&q=80",
            description="An analysis of the open-source AI movement and its impact on the industry.",
        ),
    ]

    db.add_all(videos_issue1 + videos_issue2)
    db.commit()
    db.close()
    print("Database seeded successfully.")


if __name__ == "__main__":
    seed()
