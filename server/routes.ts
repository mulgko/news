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
        title: "2025년 AI의 미래 전망",
        summary:
          "인공지능이 빠르게 발전하고 있습니다. 내년에 어떤 변화가 예상되는지 알아보세요.",
        content:
          "인공지능이 빠르게 발전하고 있습니다. 내년에 어떤 변화가 예상되는지 알아보세요. 전문가들은 생성형 모델과 자율 에이전트 분야에서 주요 돌파구를 예상하고 있습니다. AI의 일상생활 통합이 더욱 원활해지며 의료, 금융 등 다양한 산업에 영향을 미칠 것입니다.",
        category: "기술",
        imageUrl:
          "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "인플레이션 완화로 글로벌 증시 상승",
        summary: "이번 주 경제 지표 호조로 주식 시장이 신고점을 기록했습니다.",
        content:
          "이번 주 경제 지표 호조로 주식 시장이 신고점을 기록했습니다. 투자자들은 중앙은행의 다음 움직임에 대해 낙관적입니다. 기술주를 중심으로 주요 지수가 사상 최고치를 기록했습니다.",
        category: "비즈니스",
        imageUrl:
          "https://images.unsplash.com/photo-1611974765270-ca12586343bb?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "생명존에 위치한 새로운 행성 발견",
        summary:
          "천문학자들이 지구와 유사한 잠재적 행성을 40광년 거리에서 발견했습니다.",
        content:
          "천문학자들이 지구와 유사한 잠재적 행성을 40광년 거리에서 발견했습니다. 글리제 12 b로 명명된 이 행성은 적색 왜성 주위를 공전하며 액체 물을 유지할 수 있는 온도를 가지고 있습니다. 제임스 웹 우주 망원경을 통한 추가 관측이 계획되어 있습니다.",
        category: "과학",
        imageUrl:
          "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "오늘 밤 숙면을 위한 5가지 팁",
        summary:
          "숙면을 취하기 어려우신가요? 과학적으로 검증된 팁을 확인하세요.",
        content:
          "숙면을 취하기 어려우신가요? 과학적으로 검증된 팁을 확인하세요. 1. 규칙적인 일정 유지하기. 2. 편안한 환경 조성하기. 3. 취침 전 화면 시간 제한하기. 4. 먹는 음식과 마시는 음료 주의하기. 5. 일상 생활에 신체 활동 포함하기.",
        category: "건강",
        imageUrl:
          "https://images.unsplash.com/photo-1541781777621-794453259724?auto=format&fit=crop&q=80&w=800",
      },
      {
        title: "올여름 볼만한 기대작 영화들",
        summary:
          "팝콘 준비하세요! 이번 시즌 가장 기대되는 영화들을 소개합니다.",
        content:
          "팝콘 준비하세요! 이번 시즌 가장 기대되는 영화들을 소개합니다. 슈퍼히어로 대작부터 따뜻한 감동 애니메이션까지 모두를 위한 작품이 준비되어 있습니다. 이번 여름 극장에서 볼 수 있는 필람 영화 목록을 확인해보세요.",
        category: "엔터테인먼트",
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
