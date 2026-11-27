import { jsonResponse, verifySession } from '../_lib/auth.js';
import { commitFileToGitHub } from '../_lib/github.js';

export async function onRequestPost({ request, env }) {
  const authenticated = await verifySession(request, env);
  if (!authenticated) {
    return jsonResponse({ error: 'Sesi habis atau belum login.' }, 401);
  }

  let data;
  try {
    data = await request.json();
  } catch {
    return jsonResponse({ error: 'Invalid JSON' }, 400);
  }

  const jsonStr = JSON.stringify(data, null, 2);
  const bytes = new TextEncoder().encode(jsonStr);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  const base64Content = btoa(binary);

  try {
    await commitFileToGitHub(
      env,
      'data/projects.json',
      base64Content,
      'Update projects.json via Admin Panel VR'
    );
    return jsonResponse({
      ok: true,
      message: 'Berhasil disimpan ke GitHub! Cloudflare akan otomatis rebuild.',
    });
  } catch (err) {
    return jsonResponse({ error: err.message }, 500);
  }
}
