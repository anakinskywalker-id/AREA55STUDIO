import { jsonResponse, verifySession } from '../_lib/auth.js';

export async function onRequestGet({ request, env }) {
  const authenticated = await verifySession(request, env);
  return jsonResponse({ authenticated }, authenticated ? 200 : 401);
}
