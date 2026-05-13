import { NextRequest, NextResponse } from "next/server";

const WS_KEY = process.env.AMAP_WS_KEY || "1e27a8b4c1feeeb7ff5c548d169a54de";

export async function GET(req: NextRequest) {
  const keyword = req.nextUrl.searchParams.get("keyword");
  if (!keyword) return NextResponse.json({ poi: null });

  const url =
    `https://restapi.amap.com/v3/place/text` +
    `?key=${WS_KEY}` +
    `&keywords=${encodeURIComponent(keyword)}` +
    `&datatype=json`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    if (data.status === "1" && Array.isArray(data.pois) && data.pois.length > 0) {
      const poi = data.pois[0];
      return NextResponse.json({ poi });
    }
    return NextResponse.json({ poi: null });
  } catch {
    return NextResponse.json({ poi: null });
  }
}
