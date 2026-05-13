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
    tags: ["axis", "food", "非遗"],
    geo_point: { lat: 26.0835, lng: 119.2964 }
  },
  {
    id: "nanhou-street-north-archway",
    name: "南后街北口牌坊",
    summary: "三坊七巷最醒目的入口地标之一，适合拍摄牌坊和街巷纵深。",
    tags: ["photo-spot", "landmark", "entrance", "牌坊"],
    geo_point: { lat: 26.0855, lng: 119.2962 }
  },
  {
    id: "linjuemin-bingxin",
    name: "林觉民·冰心故居",
    summary: "从《与妻书》、近代家国记忆和冰心文学启蒙切入的重点故居。",
    tags: ["history", "literature", "近代史"],
    geo_point: { lat: 26.085355, lng: 119.29583 }
  },
  {
    id: "yanfu-former-residence",
    name: "严复故居",
    summary: "串联福州近代思想文化、翻译与教育主题的名人故居。",
    tags: ["history", "education", "思想史"],
    geo_point: { lat: 26.085189, lng: 119.297237 }
  },
  {
    id: "shenbaozhen-former-residence",
    name: "沈葆桢故居",
    summary: "适合讲晚清海防、船政和福州近代化背景的故居节点。",
    tags: ["history", "shipbuilding", "近代化"],
    geo_point: { lat: 26.081818, lng: 119.298163 }
  },
  {
    id: "xiaohuanglou",
    name: "小黄楼",
    summary: "适合讲解马鞍墙、天井、木构细节与闽都生活美学。",
    tags: ["architecture", "courtyard", "古厝"],
    geo_point: { lat: 26.083688, lng: 119.297578 }
  },
  {
    id: "shuixie-stage",
    name: "水榭戏台",
    summary: "非遗演艺、闽剧和夜游体验的代表性讲解点。",
    tags: ["performance", "night", "非遗"],
    geo_point: { lat: 26.083461, lng: 119.29593 }
  },
  {
    id: "yijin-lane",
    name: "衣锦坊",
    summary: "三坊之一，可用来解释\"西三坊、东七巷\"的街区格局。",
    tags: ["three-lanes", "urban-pattern", "坊巷格局"],
    geo_point: { lat: 26.083383, lng: 119.296582 }
  },
  {
    id: "wenru-lane",
    name: "文儒坊",
    summary: "三坊之一，名称带有文教与儒学意味，可衔接严复、林觉民等人物故事。",
    tags: ["three-lanes", "history", "education", "坊巷格局"],
    geo_point: { lat: 26.081801, lng: 119.296226 }
  },
  {
    id: "guanglu-lane",
    name: "光禄坊",
    summary: "三坊之一，相对安静，适合引导游客放慢脚步观察古厝细节与院落空间。",
    tags: ["three-lanes", "architecture", "古厝"],
    geo_point: { lat: 26.079605, lng: 119.295699 }
  },
  {
    id: "yangqiao-alley",
    name: "杨桥巷",
    summary: "七巷最北端，靠近北部入口，适合用来解释进入街区后的第一重历史巷道。",
    tags: ["seven-alleys", "entrance", "坊巷格局"],
    geo_point: { lat: 26.0856, lng: 119.2973 }
  },
  {
    id: "langguan-alley",
    name: "郎官巷",
    summary: "七巷之一，可引出仕宦文化和名人资源，适合作为东侧七巷的开篇。",
    tags: ["seven-alleys", "history", "坊巷格局"],
    geo_point: { lat: 26.084918, lng: 119.296395 }
  },
  {
    id: "ta-alley",
    name: "塔巷",
    summary: "七巷之一，适合亲子讲解，让孩子找巷名、认门楼、观察巷道尺度。",
    tags: ["seven-alleys", "family", "坊巷格局"],
    geo_point: { lat: 26.084351, lng: 119.29756 }
  },
  {
    id: "huang-alley",
    name: "黄巷",
    summary: "七巷之一，适合安排古厝细部观察和建筑摄影。",
    tags: ["seven-alleys", "photo", "马鞍墙"],
    geo_point: { lat: 26.083463, lng: 119.29782 }
  },
  {
    id: "anmin-alley",
    name: "安民巷",
    summary: "七巷之一，适合作为节奏较缓的过渡段，提醒游客注意人流和台阶。",
    tags: ["seven-alleys", "relaxed", "坊巷格局"],
    geo_point: { lat: 26.082399, lng: 119.297924 }
  },
  {
    id: "gong-alley",
    name: "宫巷",
    summary: "七巷之一，保存有传统宅院空间，可衔接沈葆桢故居。",
    tags: ["seven-alleys", "architecture", "residence", "古厝"],
    geo_point: { lat: 26.081545, lng: 119.298664 }
  },
  {
    id: "jipi-alley",
    name: "吉庇巷",
    summary: "七巷最南端，可作为从核心街区收束到澳门路、林则徐纪念馆方向的节点。",
    tags: ["seven-alleys", "nearby", "坊巷格局"],
    geo_point: { lat: 26.080267, lng: 119.298093 }
  },
  {
    id: "heart-tree",
    name: "爱心树",
    summary: "三坊七巷里辨识度较高的网红打卡点，适合情侣合影和社交平台分享。",
    tags: ["photo-spot", "romance", "网红", "打卡"],
    geo_point: { lat: 26.081504, lng: 119.297034 }
  },
  {
    id: "fuzhou-intangible-heritage",
    name: "福州非遗展示点",
    summary: "可把油纸伞、软木画、脱胎漆器、闽剧等内容作为互动问答素材。",
    tags: ["intangible-heritage", "craft", "互动"],
    geo_point: { lat: 26.082827, lng: 119.296691 }
  },
  {
    id: "linzexu-memorial-nearby",
    name: "林则徐纪念馆（邻近延伸）",
    summary: "三坊七巷南侧邻近延伸点，适合做半日游近代名人主题闭环。",
    tags: ["nearby", "history", "半日游"],
    geo_point: { lat: 26.07955, lng: 119.2957 }
  }
];

export const dashboardMetrics = {
  visitors: "2,847",
  satisfaction: "4.6",
  cost: "$12.4",
  cache: "78%",
  p95: "1.84s"
};
