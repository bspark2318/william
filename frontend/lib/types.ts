export interface Story {
  id: number;
  title: string;
  summary: string;
  source: string;
  url: string;
  image_url?: string;
  date: string;
  tags?: string[];
  display_order: number;
}

export interface FeaturedVideo {
  id: number;
  title: string;
  video_url: string;
  thumbnail_url: string;
  description?: string;
}

export interface Issue {
  id: number;
  week_of: string;
  title: string;
  stories: Story[];
  featured_video: FeaturedVideo | null;
  featured_videos?: FeaturedVideo[];
}

export interface IssueListItem {
  id: number;
  week_of: string;
  title: string;
}
