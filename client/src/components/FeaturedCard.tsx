import { Link } from "wouter";
import { format } from "date-fns";
import type { Post } from "@shared/schema";
import { Badge } from "@/components/ui/badge";

export function FeaturedCard({ post }: { post: Post }) {
  return (
    <Link href={`/article/${post.id}`} className="group block h-full">
      <article className="relative h-[500px] md:h-[600px] w-full overflow-hidden rounded-xl shadow-xl hover:shadow-2xl transition-all duration-500">
        <div className="absolute inset-0">
          <img 
            src={post.imageUrl} 
            alt={post.title}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent" />
        </div>
        
        <div className="absolute bottom-0 left-0 p-6 md:p-10 lg:p-12 w-full md:w-3/4 lg:w-2/3">
          <div className="flex items-center gap-3 mb-4">
            <Badge variant="secondary" className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-sm font-sans uppercase tracking-wider text-xs font-bold px-3 py-1">
              {post.category}
            </Badge>
            {post.createdAt && (
              <span className="text-white/80 text-sm font-sans font-medium">
                {format(new Date(post.createdAt), "MMMM d, yyyy")}
              </span>
            )}
          </div>
          
          <h2 className="text-3xl md:text-5xl lg:text-6xl font-bold text-white mb-4 leading-tight font-display drop-shadow-lg group-hover:text-white/90 transition-colors">
            {post.title}
          </h2>
          
          <p className="text-white/90 text-lg md:text-xl font-serif line-clamp-2 md:line-clamp-3 leading-relaxed drop-shadow-md max-w-2xl">
            {post.summary}
          </p>

          <div className="mt-6 flex items-center text-white/80 text-sm font-sans font-semibold tracking-wider uppercase group-hover:text-primary transition-colors">
            Read Full Story <span className="ml-2 group-hover:translate-x-1 transition-transform">→</span>
          </div>
        </div>
      </article>
    </Link>
  );
}
