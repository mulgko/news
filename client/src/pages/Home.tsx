import { usePosts, useViewPost } from "@/hooks/use-posts";
import { api, buildUrl } from "@shared/routes";
import { Header } from "@/components/Header";
import { Link, useSearch, useLocation } from "wouter";
import { Loader2, Heart, Eye, ThumbsUp } from "lucide-react";
import { useState, useMemo, useEffect } from "react";
import type { Post } from "@shared/schema";

// 지역별 카테고리 정의
const KOREA_CATEGORIES = [
  { id: "전체", label: "전체" },
  { id: "정치", label: "정치" },
  { id: "경제", label: "경제" },
  { id: "과학", label: "과학" },
  { id: "연예", label: "연예" },
];

const WORLD_CATEGORIES = [
  { id: "all", label: "All" },
  { id: "Politics", label: "Politics" },
  { id: "Business", label: "Business" },
  { id: "Science", label: "Science" },
  { id: "Entertainment", label: "Entertainment" },
];

// 지역에 따른 카테고리 반환 함수
const getCategoriesForRegion = (region: string) => {
  return region === "korea" ? KOREA_CATEGORIES : WORLD_CATEGORIES;
};

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
    <div
      onClick={() => onPostClick(post.id)}
      className={`block py-3 border-b border-border/30 hover:border-primary transition-colors cursor-pointer ${
        isClicked
          ? "text-gray-400 hover:text-gray-500"
          : "text-foreground hover:text-primary"
      }`}
    >
      <div className="flex justify-between items-center">
        <span className="text-sm w-[80%] truncate leading-tight">
          {post.title}
        </span>
        <div className="flex flex-col items-end gap-1 ml-2">
          <span className="text-sm text-muted-foreground">
            {post.created_at &&
              (() => {
                const date = new Date(post.created_at);
                const year = date.getFullYear().toString().slice(-2);
                const month = date.getMonth() + 1;
                const day = date.getDate();
                return `${year}.${month}.${day}`;
              })()}
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
    </div>
  </li>
);

// localStorage에서 초기값 읽기 함수 (지역에 따라 다름)
const getInitialCategory = (region: string) => {
  const stored = localStorage.getItem("selectedCategory");
  const defaultCategory = region === "korea" ? "전체" : "all";
  return stored || defaultCategory;
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
  const [, setLocation] = useLocation();

  // 선택된 지역 상태 - localStorage에서 실시간으로 읽기
  const [selectedRegion, setSelectedRegion] = useState<string>(() => {
    const stored = localStorage.getItem("selectedRegion");
    return stored || "korea";
  });

  // localStorage 변경 감지 및 상태 업데이트
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "selectedRegion" && e.newValue) {
        setSelectedRegion(e.newValue);
      }
    };

    const handleRegionChanged = (e: CustomEvent<string>) => {
      setSelectedRegion(e.detail);
    };

    window.addEventListener("storage", handleStorageChange);
    window.addEventListener(
      "regionChanged",
      handleRegionChanged as EventListener
    );

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener(
        "regionChanged",
        handleRegionChanged as EventListener
      );
    };
  }, []);

  // 선택된 카테고리 상태 - 지역에 따라 초기값 설정
  const [selectedCategory, setSelectedCategory] = useState<string>(() => {
    return selectedRegion === "korea" ? "전체" : "all";
  });

  const { data: posts, isLoading } = usePosts(
    selectedCategory
      ? {
          search,
          region: selectedRegion,
          category:
            selectedCategory === (selectedRegion === "korea" ? "전체" : "all")
              ? undefined
              : selectedCategory,
        }
      : { search, region: selectedRegion }
  );
  const viewPost = useViewPost();

  // 클릭한 게시물 ID들을 저장할 상태 - 초기값 localStorage에서 로드
  const [clickedPosts, setClickedPosts] = useState<Set<number>>(
    getInitialClickedPosts
  );

  // 지역과 카테고리 초기화 useEffect
  useEffect(() => {
    const defaultCategory = selectedRegion === "korea" ? "전체" : "all";
    setSelectedCategory(defaultCategory);
    localStorage.setItem("selectedCategory", defaultCategory);
  }, [selectedRegion]);

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
    // 이미 클릭한 포스트는 API 호출하지 않음 (중복 조회수 방지)
    if (clickedPosts.has(postId)) {
      // 이미 클릭했어도 페이지 이동은 허용
      setLocation(`/article/${postId}`);
      return;
    }

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

      // API 호출 성공 시에만 로컬 조회수 상태 업데이트 (UI 즉시 반영)
      setViewCounts((prev) => ({
        ...prev,
        [postId]: (prev[postId] || 0) + 1,
      }));

      // API 성공 후 페이지 이동
      setLocation(`/article/${postId}`);
    } catch (error) {
      console.error("Failed to increment view count:", error);
      // API 호출 실패 시 페이지 이동만 수행 (조회수는 증가하지 않음)
      setLocation(`/article/${postId}`);
    }
  };

  // 카테고리 선택 핸들러
  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    localStorage.setItem("selectedCategory", category);
  };

  // 현재 지역에 맞는 카테고리 가져오기
  const currentCategories = getCategoriesForRegion(selectedRegion);

  return (
    <div className="min-h-screen bg-background overflow-y-scroll">
      <Header />

      {/* 검색 중이 아닐 때만 카테고리 필터 표시 */}
      {!search && (
        <div className="max-w-2xl mx-auto px-4 py-6">
          <div className="flex flex-wrap gap-6 mb-6">
            {currentCategories.map((category) => (
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
                  selectedCategory ===
                    (selectedRegion === "korea" ? "전체" : "all") ||
                  post.category === selectedCategory
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
            게시물이 없습니다
          </p>
        )}
      </main>
    </div>
  );
}
