import { usePosts } from "@/hooks/use-posts";
import { Header } from "@/components/Header";
import { Link, useSearch } from "wouter";
import { Loader2 } from "lucide-react";

export default function Home() {
  const searchString = useSearch();
  const params = new URLSearchParams(searchString);
  const search = params.get("search") || undefined;

  const { data: posts, isLoading } = usePosts({ search });

  // Sort by newest first
  const sortedPosts = posts ? [...posts].sort((a, b) => 
    new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime()
  ) : [];

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="max-w-2xl mx-auto px-4 py-12">
        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : sortedPosts.length > 0 ? (
          <ul className="space-y-4">
            {sortedPosts.map((post) => (
              <li key={post.id}>
                <Link href={`/article/${post.id}`} className="text-lg text-foreground hover:text-primary transition-colors block py-2 border-b border-border/30 hover:border-primary">
                  {post.title}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-center text-muted-foreground py-20">No articles found</p>
        )}
      </main>
    </div>
  );
}
