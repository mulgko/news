import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, buildUrl, type PostInput } from "@shared/routes";

// API 베이스 URL 설정
const API_BASE_URL = "http://127.0.0.1:8000";

export function usePosts(params?: { category?: string; search?: string }) {
  const queryKey = [
    api.posts.list.path,
    params?.category,
    params?.search,
  ].filter(Boolean);

  return useQuery({
    queryKey,
    queryFn: async () => {
      // Build query string manually since fetch URL needs it
      const url = new URL(API_BASE_URL + api.posts.list.path);
      if (params?.category)
        url.searchParams.append("category", params.category);
      if (params?.search) url.searchParams.append("search", params.search);

      const res = await fetch(url.toString(), { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch posts");
      return api.posts.list.responses[200].parse(await res.json());
    },
  });
}

export function usePost(id: number) {
  return useQuery({
    queryKey: [api.posts.get.path, id],
    queryFn: async () => {
      const url = API_BASE_URL + buildUrl(api.posts.get.path, { id });
      const res = await fetch(url, { credentials: "include" });
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch post");
      return api.posts.get.responses[200].parse(await res.json());
    },
  });
}

export function useCreatePost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: PostInput) => {
      const res = await fetch(API_BASE_URL + api.posts.create.path, {
        method: api.posts.create.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        credentials: "include",
      });
      if (!res.ok) {
        if (res.status === 400) {
          const error = api.posts.create.responses[400].parse(await res.json());
          throw new Error(error.message);
        }
        throw new Error("Failed to create post");
      }
      return api.posts.create.responses[201].parse(await res.json());
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [api.posts.list.path] }),
  });
}
