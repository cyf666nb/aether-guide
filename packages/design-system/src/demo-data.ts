export type Atmosphere = "forest" | "lake" | "dusk" | "ocean" | "desert";

export const atmospheres: Array<{
  id: Atmosphere;
  name: string;
  accent: string;
  scene: string;
  bestFor: string;
}> = [
  { id: "forest", name: "Forest", accent: "#4F6B4A", scene: "/scenes/forest.png", bestFor: "山谷、森林公园" },
  { id: "lake", name: "Lake", accent: "#3F7B7A", scene: "/scenes/lake.png", bestFor: "湖泊、湿地" },
  { id: "dusk", name: "Dusk", accent: "#C4924A", scene: "/scenes/dusk.png", bestFor: "古厝、街巷、文博街区" },
  { id: "ocean", name: "Ocean", accent: "#2C5F7C", scene: "/scenes/ocean.png", bestFor: "海滨、岛屿" },
  { id: "desert", name: "Desert", accent: "#B8703A", scene: "/scenes/desert.png", bestFor: "戈壁、丹霞" }
];

export const fallbackLandmarks: Array<{
  id: string;
  name: string;
  summary: string;
  tags: string[];
  avg_duration_min?: number;
  geo_point?: { lat: number; lng: number };
}> = [
  {
    id: "nanhou-street",
    name: "南后街",
    summary: "三坊七巷的南北向中轴步行街，适合作为首次到访的集合点与路线起点。",
    tags: ["axis", "food", "非遗"]
  },
  {
    id: "linjuemin-bingxin",
    name: "林觉民·冰心故居",
    summary: "从《与妻书》、近代家国记忆和冰心文学启蒙切入的重点故居。",
    tags: ["history", "literature", "近代史"]
  },
  {
    id: "yanfu-former-residence",
    name: "严复故居",
    summary: "串联福州近代思想文化、翻译与教育主题的名人故居。",
    tags: ["history", "education", "思想史"]
  },
  {
    id: "shenbaozhen-former-residence",
    name: "沈葆桢故居",
    summary: "适合讲晚清海防、船政和福州近代化背景的故居节点。",
    tags: ["history", "shipbuilding", "近代化"]
  },
  {
    id: "xiaohuanglou",
    name: "小黄楼",
    summary: "适合讲解马鞍墙、天井、木构细节与闽都生活美学。",
    tags: ["architecture", "courtyard", "古厝"]
  },
  {
    id: "shuixie-stage",
    name: "水榭戏台",
    summary: "非遗演艺、闽剧和夜游体验的代表性讲解点。",
    tags: ["performance", "night", "非遗"]
  },
  {
    id: "yijin-lane",
    name: "衣锦坊",
    summary: "三坊之一，可用来解释“西三坊、东七巷”的街区格局。",
    tags: ["three-lanes", "urban-pattern", "坊巷格局"]
  },
  {
    id: "huang-alley",
    name: "黄巷",
    summary: "七巷之一，适合安排古厝细部观察和建筑摄影。",
    tags: ["seven-alleys", "photo", "马鞍墙"]
  },
  {
    id: "fuzhou-intangible-heritage",
    name: "福州非遗展示点",
    summary: "可把油纸伞、软木画、脱胎漆器、闽剧等内容作为互动问答素材。",
    tags: ["intangible-heritage", "craft", "互动"]
  },
  {
    id: "linzexu-memorial-nearby",
    name: "林则徐纪念馆（邻近延伸）",
    summary: "三坊七巷南侧邻近延伸点，适合做半日游近代名人主题闭环。",
    tags: ["nearby", "history", "半日游"]
  }
];

export const dashboardMetrics = {
  visitors: "2,847",
  satisfaction: "4.6",
  cost: "$12.4",
  cache: "78%",
  p95: "1.84s"
};
