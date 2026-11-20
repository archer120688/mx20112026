// Đếm người đang xem trang (Cloudflare Pages Function). Không lưu IP hay thông tin cá nhân:
// mỗi tab gửi một mã ngẫu nhiên, tự hết hạn sau ~90 giây. Cần gắn KV namespace tên XEM (xem github/HUONG-DAN.md).
const json = (o, s = 200) =>
  new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", "cache-control": "no-store" } });

export async function onRequestPost({ request, env }) {
  if (!env.XEM) return json({ loi: "chua gan KV XEM" }, 503);
  let id = "";
  try { id = String((await request.json()).id || ""); } catch (_) {}
  if (!/^[a-z0-9]{8,32}$/.test(id)) return json({ loi: "id sai" }, 400);
  try {
    await env.XEM.put("v:" + id, "1", { expirationTtl: 90 });
    const l = await env.XEM.list({ prefix: "v:", limit: 1000 });
    return json({ dang_xem: l.keys.length });
  } catch (e) {
    return json({ loi: "kv" }, 503);   // hết quota miễn phí thì trang tự ẩn bộ đếm
  }
}
