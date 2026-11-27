import { jsonResponse, verifySession } from '../_lib/auth.js';
import { commitFileToGitHub } from '../_lib/github.js';

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

export async function onRequestPost({ request, env }) {
  const authenticated = await verifySession(request, env);
  if (!authenticated) {
    return jsonResponse({ error: 'Sesi habis atau belum login.' }, 401);
  }

  const form = await request.formData();
  const file = form.get('file');
  const slug = String(form.get('slug') || 'general').replace(/[^a-z0-9-_]/gi, '-');

  if (!file || typeof file === 'string') {
    return jsonResponse({ error: 'File tidak ditemukan.' }, 400);
  }

  const safeName = `${Date.now()}-${file.name.replace(/[^a-z0-9._-]/gi, '_')}`;
  const repoPath = `assets/uploads/${slug}/${safeName}`;
  const buffer = await file.arrayBuffer();
  const base64Content = arrayBufferToBase64(buffer);

  try {
    await commitFileToGitHub(
      env,
      repoPath,
      base64Content,
      `Upload ${safeName} via Admin Panel VR`
    );
    return jsonResponse({ ok: true, path: repoPath });
  } catch (err) {
    return jsonResponse({ error: err.message }, 500);
  }
}
