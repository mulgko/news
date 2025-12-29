import { usePosts, useViewPost } from "@/hooks/use-posts";
import { api, buildUrl } from "@shared/routes";
import { Header } from "@/components/Header";
import { Link, useSearch } from "wouter";
import { Loader2, Heart, Eye, ThumbsUp } from "lucide-react";
import { useState, useMemo, useEffect } from "react";
import type { Post } from "@shared/schema";

const CATEGORIES = [
  { id: "전체", label: "전체" },
  { id: "기술", label: "기술" },
  { id: "비즈니스", label: "비즈니스" },
  { id: "과학", label: "과학" },
  { id: "건강", label: "건강" },
  { id: "엔터테인먼트", label: "엔터테인먼트" },
];

// 게시물 아이템 컴포넌트
const PostItem = ({
  post,
  isClicked,
  onPostClick,
}: {
  post: Post;
  isClicked: boolean;
  onPostClick: (postId: number) => void;
}) => (
  <li key={post.id}>
    <Link
      href={`/article/${post.id}`}
      onClick={() => onPostClick(post.id)}
      className={`block py-3 border-b border-border/30 hover:border-primary transition-colors ${
        isClicked
          ? "text-gray-400 hover:text-gray-500"
          : "text-foreground hover:text-primary"
      }`}
    >
      <div className="flex justify-between items-center">
        <span className="text-lg w-[70%] truncate leading-tight">
          {post.title}
        </span>
        <div className="flex flex-col items-end gap-1 ml-2">
          <span className="text-sm text-muted-foreground">
            {post.created_at &&
              new Date(post.created_at).toLocaleDateString("ko-KR", {
                month: "short",
                day: "numeric",
              })}
          </span>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <ThumbsUp className="w-3 h-3" />
              {post.likes || 0}
            </span>
            <span className="flex items-center gap-1">
              <Eye className="w-3 h-3" />
              {post.views || 0}
            </span>
          </div>
        </div>
      </div>
    </Link>
  </li>
);

// localStorage에서 초기값 읽기 함수
const getInitialCategory = () => {
  const stored = localStorage.getItem("selectedCategory");
  return stored || "전체";
};

const getInitialClickedPosts = (): Set<number> => {
  const stored = localStorage.getItem("clickedPosts");
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      return new Set<number>(parsed);
    } catch (error) {
      console.error("Failed to parse clickedPosts from localStorage:", error);
      return new Set<number>();
    }
  }
  return new Set<number>();
};

export default function Home() {
  const searchString = useSearch();
  const params = new URLSearchParams(searchString);
  const search = params.get("search") || undefined;

  const { data: posts, isLoading } = usePosts({ search });
  const viewPost = useViewPost();

  // 클릭한 게시물 ID들을 저장할 상태 - 초기값 localStorage에서 로드
  const [clickedPosts, setClickedPosts] = useState<Set<number>>(
    getInitialClickedPosts
  );

  // 선택된 카테고리 상태 - 초기값 localStorage에서 로드
  const [selectedCategory, setSelectedCategory] =
    useState<string>(getInitialCategory);

  // 조회수 정보를 로컬로 관리 (순서 변경 방지)
  const [viewCounts, setViewCounts] = useState<Record<number, number>>({});

  // posts가 로드되면 기존 조회수 정보 초기화
  useEffect(() => {
    if (posts) {
      const counts: Record<number, number> = {};
      posts.forEach((post) => {
        counts[post.id] = post.views || 0;
      });
      setViewCounts(counts);
    }
  }, [posts]);

  // 게시물 클릭 핸들러
  const handlePostClick = async (postId: number) => {
    const newClickedPosts = new Set(clickedPosts);
    newClickedPosts.add(postId);
    setClickedPosts(newClickedPosts);

    // localStorage에 저장
    localStorage.setItem(
      "clickedPosts",
      JSON.stringify(Array.from(newClickedPosts))
    );

    // 조회수 증가 API 호출 및 로컬 상태 업데이트
    try {
      await viewPost.mutateAsync(postId);

      // 로컬 조회수 상태 업데이트 (UI 즉시 반영)
      setViewCounts((prev) => ({
        ...prev,
        [postId]: (prev[postId] || 0) + 1,
      }));
    } catch (error) {
      console.error("Failed to increment view count:", error);
    }
  };

  // 카테고리 선택 핸들러
  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    localStorage.setItem("selectedCategory", category);
  };

  return (
    <div className="min-h-screen bg-background overflow-y-scroll">
      <Header />

      {/* 검색 중이 아닐 때만 카테고리 필터 표시 */}
      {!search && (
        <div className="max-w-2xl mx-auto px-4 py-6">
          <div className="flex flex-wrap gap-6 mb-6">
            {CATEGORIES.map((category) => (
              <button
                key={category.id}
                onClick={() => handleCategoryChange(category.id)}
                className={`py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-0 ${
                  selectedCategory === category.id
                    ? "text-primary"
                    : "text-muted-foreground"
                }`}
              >
                {category.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <main className="max-w-2xl mx-auto px-4 py-12">
        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : posts && posts.length > 0 ? (
          <ul className="space-y-4">
            {posts
              .filter(
                (post) =>
                  selectedCategory === "전체" ||
                  post.category === selectedCategory
              )
              .sort(
                (a, b) =>
                  new Date(b.created_at || 0).getTime() -
                  new Date(a.created_at || 0).getTime()
              )
              .map((post) => {
                const isClicked = clickedPosts.has(post.id);
                // 로컬 조회수 정보와 병합
                const postWithLocalViews = {
                  ...post,
                  views: viewCounts[post.id] || post.views || 0,
                };
                return (
                  <PostItem
                    key={post.id}
                    post={postWithLocalViews}
                    isClicked={isClicked}
                    onPostClick={handlePostClick}
                  />
                );
              })}
          </ul>
        ) : (
          <p className="text-center text-muted-foreground py-20">
            검색 결과를 찾을 수 없습니다.
          </p>
        )}
      </main>
    </div>
  );
}
