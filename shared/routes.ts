import { z } from "zod";
import { insertPostSchema, posts } from "./schema";

export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
};

export const api = {
  posts: {
    list: {
      method: "GET" as const,
      path: "/api/posts",
      input: z
        .object({
          category: z.string().optional(),
          search: z.string().optional(),
        })
        .optional(),
      responses: {
        200: z.array(z.custom<typeof posts.$inferSelect>()),
      },
    },
    get: {
      method: "GET" as const,
      path: "/api/posts/{id}", // :id -> {id}
      responses: {
        200: z.custom<typeof posts.$inferSelect>(),
        404: errorSchemas.notFound,
      },
    },
    create: {
      method: "POST" as const,
      path: "/api/posts",
      input: insertPostSchema,
      responses: {
        201: z.custom<typeof posts.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
  },
};

export function buildUrl(
  path: string,
  params?: Record<string, string | number>
): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url = url.replace(`{${key}}`, String(value)); // :key -> {key}
    });
  }
  return url;
}

export type PostInput = z.infer<typeof api.posts.create.input>;
export type PostResponse = z.infer<(typeof api.posts.create.responses)[201]>;
