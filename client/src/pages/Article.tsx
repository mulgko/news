import { useRoute } from "wouter";
import { usePost } from "@/hooks/use-posts";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import { format } from "date-fns";

export default function Article() {
  const [, params] = useRoute("/article/:id");
  const id = params ? parseInt(params.id) : 0;
  const { data: post, isLoading, error } = usePost(id);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-4xl font-display font-bold mb-4">404</h1>
            <p className="text-muted-foreground font-serif text-lg">
              Article not found.
            </p>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col overflow-y-scroll">
      <Header />

      <main className="flex-1 max-w-2xl mx-auto px-4 py-12">
        {/* Meta info */}
        <div className="flex items-center gap-4 text-sm text-gray-500 pb-4">
          <span>
            {post.created_at &&
              format(new Date(post.created_at), "yyyy년 M월 d일")}
          </span>
        </div>

        {/* Simple Header */}
        <div className="bg-background border-b border-border">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-3xl md:text-4xl font-bold font-display text-foreground md:leading-[1.5] mb-8">
              {post.title}
            </h1>
          </div>
        </div>

        {/* Content Section */}
        <article className="max-w-3xl mx-auto py-12">
          {/* Article Body */}
          <div className="text-foreground leading-relaxed space-y-4">
            {post.content.split("\n").map(
              (paragraph, idx) =>
                paragraph.trim() && (
                  <p key={idx} className="text-base">
                    {paragraph}
                  </p>
                )
            )}
          </div>
        </article>
      </main>

      {/* <Footer /> */}
    </div>
  );
}
