import { usePosts } from "@/hooks/use-posts";
import { Header } from "@/components/Header";
import { Link, useSearch } from "wouter";
import { Loader2 } from "lucide-react";
import { useState } from "react";

const CATEGORIES = [
  { id: "전체", label: "전체" },
  { id: "기술", label: "기술" },
  { id: "비즈니스", label: "비즈니스" },
  { id: "과학", label: "과학" },
  { id: "건강", label: "건강" },
  { id: "엔터테인먼트", label: "엔터테인먼트" },
];

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

  // 클릭한 게시물 ID들을 저장할 상태 - 초기값 localStorage에서 로드
  const [clickedPosts, setClickedPosts] = useState<Set<number>>(
    getInitialClickedPosts
  );

  // 선택된 카테고리 상태 - 초기값 localStorage에서 로드
  const [selectedCategory, setSelectedCategory] =
    useState<string>(getInitialCategory);

  // 게시물 클릭 핸들러
  const handlePostClick = (postId: number) => {
    const newClickedPosts = new Set(clickedPosts);
    newClickedPosts.add(postId);
    setClickedPosts(newClickedPosts);

    // localStorage에 저장
    localStorage.setItem(
      "clickedPosts",
      JSON.stringify(Array.from(newClickedPosts))
    );
  };

  // 카테고리 선택 핸들러
  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    localStorage.setItem("selectedCategory", category);
  };

  // Sort by newest first and filter by category
  const sortedPosts = posts
    ? [...posts]
        .filter(
          (post) =>
            selectedCategory === "전체" || post.category === selectedCategory
        )
        .sort(
          (a, b) =>
            new Date(b.created_at || 0).getTime() -
            new Date(a.created_at || 0).getTime()
        )
    : [];

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
        ) : sortedPosts.length > 0 ? (
          <ul className="space-y-4">
            {sortedPosts.map((post) => {
              const isClicked = clickedPosts.has(post.id);

              return (
                <li key={post.id}>
                  <Link
                    href={`/article/${post.id}`}
                    onClick={() => handlePostClick(post.id)}
                    className={`flex justify-between text-lg transition-colors block py-2 border-b border-border/30 hover:border-primary ${
                      isClicked
                        ? "text-gray-400 hover:text-gray-500"
                        : "text-foreground hover:text-primary"
                    }`}
                  >
                    <span className="w-[70%] truncate">{post.title}</span>
                    <span className="text-sm text-muted-foreground">1분전</span>
                  </Link>
                </li>
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
