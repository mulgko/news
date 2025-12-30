import { Link, useLocation } from "wouter";
import { Search, Sun, Moon, Globe, MapPin } from "lucide-react";
import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { Input } from "@/components/ui/input";

export function Header() {
  const [search, setSearch] = useState("");
  const [, setLocation] = useLocation();
  const { theme, setTheme } = useTheme();

  // 지역 선택 상태 - localStorage와 동기화
  const getInitialRegion = () => {
    const stored = localStorage.getItem("selectedRegion");
    return stored || "korea";
  };

  const [selectedRegion, setSelectedRegion] =
    useState<string>(getInitialRegion);

  // localStorage 변경 감지 및 상태 업데이트
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "selectedRegion" && e.newValue) {
        setSelectedRegion(e.newValue);
      }
    };

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, []);

  // 지역 변경 핸들러 - 양방향 토글
  const handleRegionChange = (clickedRegion: string) => {
    // 어느 버튼을 누르더라도 현재 상태와 반대로 토글
    const newRegion = selectedRegion === "korea" ? "world" : "korea";
    setSelectedRegion(newRegion);
    localStorage.setItem("selectedRegion", newRegion);
    window.dispatchEvent(
      new CustomEvent("regionChanged", { detail: newRegion })
    );
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    const trimmedValue = value.trim(); // 앞뒤 공백만 제거
    if (trimmedValue) {
      setLocation(`/?search=${encodeURIComponent(trimmedValue)}`);
    } else {
      setLocation("/");
    }
  };

  return (
    <header className="border-b border-gray-100 dark:border-gray-900 py-6">
      <div className="max-w-2xl mx-auto px-4 flex items-center justify-between">
        <Link href="/" className="block">
          <h1 className="text-3xl font-black text-foreground cursor-pointer">
            NEXT
          </h1>
        </Link>

        <div className="flex items-center gap-4">
          {/* 지역 선택 토글 - iOS 스타일 애니메이션 */}
          <div className="relative flex bg-muted/80 rounded-2xl p-0.5 shadow-inner border border-border/50 backdrop-blur-sm overflow-hidden">
            {/* 애니메이션되는 배경 */}
            <div
              className={`absolute top-0.5 bottom-0.5 bg-gradient-to-r rounded-xl shadow-lg transition-all duration-300 ease-in-out ${
                selectedRegion === "korea"
                  ? "left-0.5 right-1/2 from-blue-500 to-blue-600"
                  : "left-1/2 right-0.5 from-green-500 to-green-600"
              }`}
            />

            {/* 한국 버튼 */}
            <button
              onClick={() => handleRegionChange("korea")}
              className={`relative flex items-center gap-0.5 px-2 py-1 text-xs font-medium rounded-sm transition-all duration-300 z-10 ${
                selectedRegion === "korea"
                  ? "text-white"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <MapPin className="w-2.5 h-2.5" />
              한국
            </button>

            {/* 세계 버튼 */}
            <button
              onClick={() => handleRegionChange("world")}
              className={`relative flex items-center gap-0.5 px-2 py-1 text-xs font-medium rounded-sm transition-all duration-300 z-10 ${
                selectedRegion === "world"
                  ? "text-white"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Globe className="w-2.5 h-2.5" />
              세계
            </button>
          </div>

          {/* Theme Toggle Button */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="relative flex items-center justify-center w-9 h-9 rounded-full hover:bg-secondary transition-colors focus:outline-none"
            aria-label="테마 전환"
          >
            <Sun className="w-5 h-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute w-5 h-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">테마 전환</span>
          </button>

          <div className="relative">
            <Input
              type="text"
              placeholder="검색하기.."
              className="w-48 pl-4 pr-10 focus:ring-0 focus:outline-none focus:border-primary focus-visible:ring-0 focus-visible:ring-offset-0"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
            />
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          </div>
        </div>
      </div>
    </header>
  );
}
