import { pgTable, text, serial, timestamp, integer } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const posts = pgTable("posts", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  summary: text("summary").notNull(),
  content: text("content").notNull(),
  category: text("category").notNull(),
  region: text("region").notNull(),
  image_url: text("image_url").notNull(),
  url: text("url"),
  created_at: timestamp("created_at").defaultNow(),
  likes: integer("likes").default(0),
  dislikes: integer("dislikes").default(0),
  views: integer("views").default(0),
});

export const insertPostSchema = createInsertSchema(posts).omit({
  id: true,
  created_at: true,
});

export type Post = typeof posts.$inferSelect;
export type InsertPost = z.infer<typeof insertPostSchema>;
