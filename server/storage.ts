import { db } from "./db";
import { posts, type InsertPost, type Post } from "@shared/schema";
import { eq, ilike, or, sql } from "drizzle-orm";

export interface IStorage {
  getPosts(options?: { category?: string; search?: string }): Promise<Post[]>;
  getPost(id: number): Promise<Post | undefined>;
  createPost(post: InsertPost): Promise<Post>;
  incrementViews(id: number): Promise<void>;
  incrementLikes(id: number): Promise<void>;
}

export class DatabaseStorage implements IStorage {
  async getPosts(options?: {
    category?: string;
    search?: string;
  }): Promise<Post[]> {
    let query = db.select().from(posts);

    if (options?.category) {
      query = query.where(eq(posts.category, options.category)) as any;
    }

    if (options?.search) {
      const searchLower = `%${options.search.toLowerCase()}%`;
      query = query.where(
        or(ilike(posts.title, searchLower), ilike(posts.content, searchLower))
      ) as any;
    }

    // Sort by newest first
    return await query.orderBy(posts.created_at);
  }

  async getPost(id: number): Promise<Post | undefined> {
    const [post] = await db.select().from(posts).where(eq(posts.id, id));
    return post;
  }

  async createPost(post: InsertPost): Promise<Post> {
    const [newPost] = await db.insert(posts).values(post).returning();
    return newPost;
  }

  async incrementViews(id: number): Promise<void> {
    await db
      .update(posts)
      .set({ views: sql`${posts.views} + 1` })
      .where(eq(posts.id, id));
  }

  async incrementLikes(id: number): Promise<void> {
    await db
      .update(posts)
      .set({ likes: sql`${posts.likes} + 1` })
      .where(eq(posts.id, id));
  }
}

export const storage = new DatabaseStorage();
