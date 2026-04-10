import Image from "next/image";
import { FeaturedVideo } from "@/lib/types";

interface VideoPreviewProps {
  video: FeaturedVideo;
  showLabel?: boolean;
}

export default function VideoPreview({ video, showLabel = false }: VideoPreviewProps) {
  return (
    <div className="group">
      {showLabel && (
        <div className="divider-label">
          <span className="text-[11px] text-ink-light uppercase tracking-[0.2em] font-body whitespace-nowrap font-semibold">
            Featured Videos
          </span>
        </div>
      )}

      <a
        href={video.video_url}
        target="_blank"
        rel="noopener noreferrer"
        className="block"
      >
        <div className="border border-rule overflow-hidden">
          <div className="aspect-video relative overflow-hidden bg-paper-alt">
            <Image
              src={video.thumbnail_url}
              alt={video.title}
              fill
              sizes="300px"
              className="object-cover group-hover:opacity-90 transition-opacity duration-300"
            />

            {/* Play button overlay */}
            <div className="absolute inset-0 flex items-center justify-center bg-ink/10 group-hover:bg-ink/5 transition-all duration-300">
              <div className="w-12 h-12 rounded-full bg-white/90 flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-300">
                <svg
                  className="w-5 h-5 text-ink ml-0.5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Title bar */}
          <div className="p-3 bg-paper-alt border-t border-rule">
            <h4 className="font-headline text-sm font-bold text-ink leading-snug">
              {video.title}
            </h4>
            {video.description && (
              <p className="text-xs text-ink-light mt-1 line-clamp-2">
                {video.description}
              </p>
            )}
            <span className="inline-block mt-2 text-[10px] text-accent uppercase tracking-wider font-semibold">
              Watch video &#x2192;
            </span>
          </div>
        </div>
      </a>
    </div>
  );
}
