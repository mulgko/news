import { Link } from "wouter";
import { format } from "date-fns";
import type { Post } from "@shared/schema";
import { Badge } from "@/components/ui/badge";

export function NewsCard({ post }: { post: Post }) {
  return (
    <Link href={`/article/${post.id}`} className="group block">
      <article className="bg-card h-full flex flex-col overflow-hidden border-b border-border/50 pb-6 group-hover:border-primary/20 transition-colors">
        <div className="relative aspect-[16/10] overflow-hidden rounded-lg mb-5 bg-muted">
          <img 
            src={post.imageUrl} 
            alt={post.title}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
          <Badge className="absolute top-4 left-4 bg-white/90 text-black hover:bg-white backdrop-blur shadow-sm font-sans uppercase text-[10px] tracking-wider">
            {post.category}
          </Badge>
        </div>
        
        <div className="flex-1 flex flex-col">
          <div className="flex items-center gap-2 text-xs font-sans font-medium text-muted-foreground mb-3 uppercase tracking-wide">
            {post.createdAt && format(new Date(post.createdAt), "MMMM d, yyyy")}
          </div>
          
          <h3 className="text-2xl font-bold mb-3 leading-tight font-display group-hover:text-primary transition-colors">
            {post.title}
          </h3>
          
          <p className="text-muted-foreground font-serif leading-relaxed line-clamp-3 mb-4 text-[15px]">
            {post.summary}
          </p>
          
          <div className="mt-auto pt-2">
            <span className="text-xs font-bold uppercase tracking-widest text-primary group-hover:underline decoration-1 underline-offset-4">
              Read Article
            </span>
          </div>
        </div>
      </article>
    </Link>
  );
}
