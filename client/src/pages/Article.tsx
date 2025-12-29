import { useRoute, Link } from "wouter";
import { useState } from "react";
import { usePost, useLikePost, useDislikePost } from "@/hooks/use-posts";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  ArrowLeft,
  Sparkles,
  Heart,
  ExternalLink,
} from "lucide-react";
import { format } from "date-fns";

// localStorage에서 좋아요/싫어요 누른 게시물 ID들 가져오기
const getLikedPosts = (): Set<number> => {
  const stored = localStorage.getItem("likedPosts");
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      return new Set<number>(parsed);
    } catch (error) {
      console.error("Failed to parse likedPosts from localStorage:", error);
      return new Set<number>();
    }
  }
  return new Set<number>();
};

const getDislikedPosts = (): Set<number> => {
  const stored = localStorage.getItem("dislikedPosts");
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      return new Set<number>(parsed);
    } catch (error) {
      console.error("Failed to parse dislikedPosts from localStorage:", error);
      return new Set<number>();
    }
  }
  return new Set<number>();
};

export default function Article() {
  const [, params] = useRoute("/article/:id");
  const id = params ? parseInt(params.id) : 0;
  const { data: post, isLoading, error } = usePost(id);
  const likePost = useLikePost();
  const dislikePost = useDislikePost();

  // 좋아요/싫어요 누른 게시물 상태 관리
  const [likedPosts, setLikedPosts] = useState<Set<number>>(getLikedPosts);
  const [dislikedPosts, setDislikedPosts] =
    useState<Set<number>>(getDislikedPosts);
  const isLiked = likedPosts.has(id);
  const isDisliked = dislikedPosts.has(id);

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
              페이지를 찾을 수 없네요. 😰
            </p>
          </div>
        </div>
        {/* <Footer /> */}
      </div>
    );
  }

  return (
    <div className="h-screen bg-background flex flex-col overflow-y-auto">
      <Header />

      <main className="flex-1 max-w-2xl mx-auto px-4 py-12">
        {/* Back Button */}
        <div className="mb-6">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </div>

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

        {/* AI Summary Section */}
        <div className="max-w-3xl mx-auto py-8">
          <div className="bg-muted/30 rounded-lg p-6 border-l-4 border-primary">
            <h2 className="text-lg font-semibold text-foreground mb-3 font-display flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary animate-pulse" />
              AI 요약
            </h2>
            <div className="text-foreground/85 leading-relaxed">
              {post.content ? (
                <div className="space-y-2">
                  <p className="text-base">
                    {post.content.length > 200
                      ? `${post.content.substring(0, 200)}...`
                      : post.content}
                  </p>
                </div>
              ) : (
                <p className="text-muted-foreground italic">
                  요약을 생성할 수 없습니다.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Like/Dislike Button Section */}
        <div className="max-w-3xl mx-auto py-4">
          <div className="flex gap-4 justify-center">
            {/* 좋아요 버튼 */}
            <button
              onClick={() => {
                if (!isLiked) {
                  likePost.mutate(id, {
                    onSuccess: () => {
                      const newLikedPosts = new Set(likedPosts);
                      newLikedPosts.add(id);
                      setLikedPosts(newLikedPosts);
                      localStorage.setItem(
                        "likedPosts",
                        JSON.stringify(Array.from(newLikedPosts))
                      );
                    },
                  });
                }
              }}
              disabled={likePost.isPending || isLiked}
              className="flex flex-col items-center gap-1 p-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-transparent"
            >
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center text-lg ${
                  isLiked
                    ? "bg-blue-100 text-blue-600"
                    : "bg-gray-100 hover:bg-gray-200 text-gray-600"
                }`}
              >
                🥰
              </span>
              <span className="text-xs font-medium text-gray-600">
                좋아요 {post.likes || 0}
              </span>
            </button>

            {/* 싫어요 버튼 */}
            <button
              onClick={() => {
                if (!isDisliked) {
                  dislikePost.mutate(id, {
                    onSuccess: () => {
                      const newDislikedPosts = new Set(dislikedPosts);
                      newDislikedPosts.add(id);
                      setDislikedPosts(newDislikedPosts);
                      localStorage.setItem(
                        "dislikedPosts",
                        JSON.stringify(Array.from(newDislikedPosts))
                      );
                    },
                  });
                }
              }}
              disabled={dislikePost.isPending || isDisliked}
              className="flex flex-col items-center gap-1 p-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-transparent"
            >
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center text-lg ${
                  isDisliked
                    ? "bg-red-100 text-red-600"
                    : "bg-gray-100 hover:bg-gray-200 text-gray-600"
                }`}
              >
                😰
              </span>
              <span className="text-xs font-medium text-gray-600">
                싫어요 {post.dislikes || 0}
              </span>
            </button>
          </div>
        </div>

        {/* Content Section */}
        <article className="max-w-3xl mx-auto py-12">
          {/* Original Article Link */}
          {post.url && (
            <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
              <a
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium transition-colors"
              >
                <ExternalLink className="w-4 h-4" />
                기사 원문 보기
              </a>
            </div>
          )}

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
