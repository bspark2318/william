import { Story } from "@/lib/types";
import StoryCard from "./StoryCard";

interface StoryFeedProps {
  stories: Story[];
}

export default function StoryFeed({ stories }: StoryFeedProps) {
  const sorted = [...stories].sort((a, b) => a.display_order - b.display_order);

  return (
    <div>
      {sorted.map((story, i) => (
        <div
          key={story.id}
          className={`animate-fade-in-up stagger-${Math.min(i + 1, 5)}`}
        >
          <StoryCard story={story} />
          {i < sorted.length - 1 && <hr className="divider-rule" />}
        </div>
      ))}
    </div>
  );
}
