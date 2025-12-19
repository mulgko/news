import type { Express } from "express";
import type { Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { z } from "zod";

async function seedDatabase() {
  const existingPosts = await storage.getPosts();
  if (existingPosts.length === 0) {
    const seedPosts = [
      {
        title: "The Future of AI in 2025asdfasdf",
        summary:
          "Artificial Intelligence is evolving rapidly. Here's what to expect in the coming year.",
        content:
          "Artificial Intelligence is evolving rapidly. Here's what to expect in the coming year. Experts predict major breakthroughs in generative models and autonomous agents. The integration of AI into daily life will become even more seamless, affecting industries from healthcare to finance.",
        category: "Technology",
        imageUrl:
          "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "Global Markets Rally as Inflation Cools",
        summary:
          "Stock markets hit new highs this week as economic data shows promising signs.",
        content:
          "Stock markets hit new highs this week as economic data shows promising signs. Investors are optimistic about the central bank's next move. Tech stocks led the charge, with major indices closing at record levels.",
        category: "Business",
        imageUrl:
          "https://images.unsplash.com/photo-1611974765270-ca12586343bb?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "New Planet Discovered in Habitable Zone",
        summary:
          "Astronomers have found a potential Earth-like planet just 40 light years away.",
        content:
          "Astronomers have found a potential Earth-like planet just 40 light years away. The planet, named Gliese 12 b, orbits a red dwarf star and has temperatures that could support liquid water. Further observations are planned with the James Webb Space Telescope.",
        category: "Science",
        imageUrl:
          "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "5 Tips for Better Sleep Tonight",
        summary:
          "Struggling to get a good night's rest? Try these science-backed tips.",
        content:
          "Struggling to get a good night's rest? Try these science-backed tips. 1. Stick to a schedule. 2. Create a restful environment. 3. Limit screen time before bed. 4. Watch what you eat and drink. 5. Include physical activity in your daily routine.",
        category: "Health",
        imageUrl:
          "https://images.unsplash.com/photo-1541781777621-794453259724?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "Upcoming Summer Blockbusters to Watchㄴㄴ",
        summary:
          "Get your popcorn ready! Here are the most anticipated movies of the season.",
        content:
          "Get your popcorn ready! Here are the most anticipated movies of the season. From superhero epics to heartwarming animated features, there's something for everyone. Check out our list of must-see films hitting theaters this summer.",
        category: "Entertainment",
        imageUrl:
          "https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&q=80&w=800",
      },
    ];

    for (const post of seedPosts) {
      await storage.createPost(post);
    }
    console.log("Database seeded with initial posts");
  }
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // Seed the database
  await seedDatabase();

  app.get(api.posts.list.path, async (req, res) => {
    const category = req.query.category as string | undefined;
    const search = req.query.search as string | undefined;
    const posts = await storage.getPosts({ category, search });
    res.json(posts);
  });

  app.get(api.posts.get.path, async (req, res) => {
    const post = await storage.getPost(Number(req.params.id));
    if (!post) {
      return res.status(404).json({ message: "Post not found" });
    }
    res.json(post);
  });

  app.post(api.posts.create.path, async (req, res) => {
    try {
      const input = api.posts.create.input.parse(req.body);
      const post = await storage.createPost(input);
      res.status(201).json(post);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({
          message: err.errors[0].message,
          field: err.errors[0].path.join("."),
        });
      }
      throw err;
    }
  });

  return httpServer;
}
