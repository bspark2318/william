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
            summary="The latest model from OpenAI demonstrates unprecedented ability to reason across text, images, and audio simultaneously. Researchers report significant improvements in scientific problem-solving and code generation tasks.",
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
            summary="AlphaFold 4 can now predict protein structures in milliseconds rather than minutes, opening the door to real-time drug discovery simulations. The pharmaceutical industry is already racing to integrate the technology.",
            source="Nature",
            url="https://nature.com",
            date="2026-04-06",
            tags=["DeepMind", "Biology", "AlphaFold"],
            display_order=2,
        ),
        Story(
            issue_id=1,
            title="EU Passes Landmark AI Liability Directive",
            summary="Companies deploying AI systems in the European Union will now face strict liability for damages caused by their models. The directive establishes a framework for compensation and mandates transparency in high-risk applications.",
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
            summary="In a bold move for open source AI, Meta has released its most capable model yet with a fully permissive license. Early benchmarks show it competing with proprietary models on reasoning and code tasks.",
            source="TechCrunch",
            url="https://techcrunch.com",
            date="2026-04-04",
            tags=["Meta", "Open Source", "Llama"],
            display_order=4,
        ),
        Story(
            issue_id=1,
            title="AI Agents Now Handle 40% of Customer Service at Major Banks",
            summary="A new report from McKinsey reveals that autonomous AI agents have reached a tipping point in financial services, handling everything from account inquiries to fraud detection with minimal human oversight.",
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
            summary="The French AI startup continues its meteoric rise with a massive new funding round.",
            source="Bloomberg",
            url="https://bloomberg.com",
            date="2026-03-31",
            tags=["Mistral", "Funding"],
            display_order=1,
        ),
        Story(
            issue_id=2,
            title="Open Source LLMs Now Match GPT-4 on Key Benchmarks",
            summary="A consortium of researchers demonstrates that open-weight models have closed the gap.",
            source="Ars Technica",
            url="https://arstechnica.com",
            date="2026-03-30",
            tags=["Open Source", "Benchmarks"],
            display_order=2,
        ),
        Story(
            issue_id=2,
            title="NVIDIA Announces Next-Gen AI Chip Architecture",
            summary="The new Blackwell Ultra architecture promises 3x inference throughput.",
            source="Wired",
            url="https://wired.com",
            date="2026-03-29",
            tags=["NVIDIA", "Hardware"],
            display_order=3,
        ),
        Story(
            issue_id=2,
            title="AI-Generated Code Now Accounts for 25% of All New Code at Google",
            summary="Internal metrics reveal the growing role of AI assistants in production codebases.",
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
