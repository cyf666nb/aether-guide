export type Atmosphere = "forest" | "lake" | "dusk" | "ocean" | "desert";

export const atmospheres: Array<{
  id: Atmosphere;
  name: string;
  accent: string;
  scene: string;
  bestFor: string;
}> = [
  { id: "forest", name: "Forest", accent: "#4F6B4A", scene: "/scenes/forest.png", bestFor: "山岳、森林公园" },
  { id: "lake", name: "Lake", accent: "#3F7B7A", scene: "/scenes/lake.png", bestFor: "湖泊、湿地" },
  { id: "dusk", name: "Dusk", accent: "#C4924A", scene: "/scenes/dusk.png", bestFor: "古镇、文博类" },
  { id: "ocean", name: "Ocean", accent: "#2C5F7C", scene: "/scenes/ocean.png", bestFor: "海滨、岛屿" },
  { id: "desert", name: "Desert", accent: "#B8703A", scene: "/scenes/desert.png", bestFor: "戈壁、丹霞" }
];

export const fallbackLandmarks = [
  {
    id: "moon-gate",
    name: "月门听泉",
    summary: "临水月门与清晨水声构成第一段讲解，适合开场。",
    tags: ["water", "garden", "photo"]
  },
  {
    id: "pine-terrace",
    name: "松台远眺",
    summary: "高处观景平台，可串联夕照、拥挤度与路线推荐。",
    tags: ["view", "history", "sunset"]
  },
  {
    id: "ink-bridge",
    name: "墨桥",
    summary: "主游线节点，适合演示对话定位和偏航提醒。",
    tags: ["bridge", "route", "family"]
  }
];

export const dashboardMetrics = {
  visitors: "2,847",
  satisfaction: "4.6",
  cost: "$12.4",
  cache: "78%",
  p95: "1.84s"
};

