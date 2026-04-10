export interface Story {
  id: number;
  title: string;
  summary: string;
  /** When present (from API), shown as bullets; otherwise `summary` is used as a single line. */
  bullet_points?: string[];
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
  edition: number;
  stories: Story[];
  featured_video: FeaturedVideo | null;
  featured_videos?: FeaturedVideo[];
}

export interface IssueListItem {
  id: number;
  week_of: string;
  title: string;
  edition: number;
}
