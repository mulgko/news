import { useRoute } from "wouter";
import { usePost } from "@/hooks/use-posts";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Badge } from "@/components/ui/badge";
import { Loader2, Calendar, User, Clock, Share2 } from "lucide-react";
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
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-1">
        {/* Hero Section */}
        <div className="relative w-full h-[50vh] md:h-[60vh] lg:h-[70vh]">
          <div className="absolute inset-0">
            <img
              src={post.imageUrl}
              alt={post.title}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent" />
          </div>

          <div className="absolute bottom-0 left-0 w-full pb-12">
            <div className="container-wide">
              <div className="max-w-4xl mx-auto">
                <Badge className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-sm font-sans uppercase tracking-wider text-sm font-bold px-4 py-1.5 mb-6">
                  {post.category}
                </Badge>
                <h1 className="text-4xl md:text-5xl lg:text-7xl font-bold font-display text-foreground leading-tight drop-shadow-sm mb-6">
                  {post.title}
                </h1>
                <p className="text-xl md:text-2xl font-serif text-foreground/80 leading-relaxed max-w-3xl drop-shadow-sm">
                  {post.summary}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Content Section */}
        <article className="container-wide py-12">
          <div className="max-w-3xl mx-auto">
            {/* Meta bar */}
            <div className="flex flex-wrap items-center justify-between gap-6 py-6 border-y border-border mb-10">
              <div className="flex items-center gap-6 text-sm text-muted-foreground font-sans font-medium uppercase tracking-wide">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  <span>Editorial Staff</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span>
                    {post.createdAt &&
                      format(new Date(post.createdAt), "MMMM d, yyyy")}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>5 min read</span>
                </div>
              </div>

              <button className="flex items-center gap-2 text-primary hover:text-primary/80 transition-colors font-sans font-bold uppercase text-xs tracking-widest">
                <Share2 className="w-4 h-4" />
                Share Article
              </button>
            </div>

            {/* Article Body */}
            <div className="prose prose-lg md:prose-xl font-serif prose-headings:font-display prose-headings:font-bold prose-headings:text-foreground prose-p:text-foreground/90 prose-p:leading-loose prose-a:text-primary prose-a:no-underline hover:prose-a:underline prose-img:rounded-xl prose-img:shadow-lg max-w-none">
              {post.content
                .split("\n")
                .map(
                  (paragraph, idx) =>
                    paragraph.trim() && <p key={idx}>{paragraph}</p>
                )}
            </div>

            {/* End Mark */}
            <div className="flex justify-center mt-16 mb-8">
              <div className="text-primary text-3xl">❦</div>
            </div>
          </div>
        </article>
      </main>

      {/* <Footer /> */}
    </div>
  );
}
