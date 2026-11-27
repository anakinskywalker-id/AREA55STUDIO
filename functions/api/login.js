import { createSessionCookie, jsonResponse } from '../_lib/auth.js';

export async function onRequestPost({ request, env }) {
  const adminPassword = env.ADMIN_PASSWORD;
  if (!adminPassword) {
    return jsonResponse(
      { error: 'ADMIN_PASSWORD belum dikonfigurasi di Cloudflare Pages.' },
      500
    );
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: 'Invalid JSON' }, 400);
  }

  if (!body.password || body.password !== adminPassword) {
    return jsonResponse({ error: 'Password salah.' }, 401);
  }

  const secret = env.SESSION_SECRET || adminPassword;
  const cookie = await createSessionCookie(secret);
  return jsonResponse(
    { ok: true },
    200,
    { 'Set-Cookie': cookie }
  );
}
