import { z } from "zod";

// Post type definition (matching Python backend SQLAlchemy model)
export interface Post {
  id: number;
  title: string;
  summary: string;
  content: string;
  category: string;
  region: string;
  image_url: string;
  url: string | null;
  created_at: string | null;
  likes: number;
  dislikes: number;
  views: number;
  ai_summary: string | null;
}

// Zod schema for post validation
export const insertPostSchema = z.object({
  title: z.string(),
  summary: z.string(),
  content: z.string(),
  category: z.string(),
  region: z.string(),
  image_url: z.string(),
  url: z.string().nullable().optional(),
  ai_summary: z.string().nullable().optional(),
});

export type InsertPost = z.infer<typeof insertPostSchema>;
