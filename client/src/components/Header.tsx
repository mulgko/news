import { Link, useLocation } from "wouter";
import { Search } from "lucide-react";
import { useState } from "react";
import { Input } from "@/components/ui/input";

export function Header() {
  const [search, setSearch] = useState("");
  const [, setLocation] = useLocation();

  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (value.trim()) {
      setLocation(`/?search=${encodeURIComponent(value)}`);
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

        <div className="relative">
          <Input
            type="text"
            placeholder="Search..."
            className="w-48 pl-4 pr-10 focus:ring-0 focus:outline-none focus:border-blue-300 focus-visible:ring-0 focus-visible:ring-offset-0"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
          />
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>
    </header>
  );
}
