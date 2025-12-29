import { Link, useLocation } from "wouter";
import { Search, Sun, Moon } from "lucide-react";
import { useState } from "react";
import { useTheme } from "next-themes";
import { Input } from "@/components/ui/input";

export function Header() {
  const [search, setSearch] = useState("");
  const [, setLocation] = useLocation();
  const { theme, setTheme } = useTheme();

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
    <header className="border-b border-border py-6">
      <div className="max-w-2xl mx-auto px-4 flex items-center justify-between">
        <Link href="/" className="block">
          <h1 className="text-3xl font-bold text-foreground cursor-pointer">
            넥
          </h1>
        </Link>

        <div className="flex items-center gap-4">
          {/* Theme Toggle Button */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="relative flex items-center justify-center w-9 h-9 rounded-full hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
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
