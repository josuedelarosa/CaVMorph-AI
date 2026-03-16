import { fetch as tauriFetch, ResponseType, Body } from '@tauri-apps/api/http'
import { readBinaryFile } from '@tauri-apps/api/fs'
import type { PredictionResult } from '../types'

export const COLLECTION_URL = 'https://bivl2ab.uis.edu.co/phenoai/api/v1/contribute'

const APP_VERSION = '0.1.0'
const MAX_BYTES = 8 * 1024 * 1024  // skip files > 8 MB

const EXT_TO_MIME: Record<string, string> = {
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png':  'image/png',
  '.webp': 'image/webp',
}

type Logger = { log: (...a: any[]) => void; warn: (...a: any[]) => void }

/** Replace NaN / Infinity with null so the JSON payload is always valid. */
function sanitizeFloats(value: unknown): unknown {
  if (typeof value === 'number') return isFinite(value) ? value : null
  if (Array.isArray(value)) return value.map(sanitizeFloats)
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(value)) out[k] = sanitizeFloats(v)
    return out
  }
  return value
}

/** Encode Uint8Array to base64 in safe chunks (avoids call-stack overflow on large arrays). */
function toBase64(bytes: Uint8Array): string {
  const CHUNK = 8192
  const parts: string[] = []
  for (let i = 0; i < bytes.length; i += CHUNK) {
    parts.push(String.fromCharCode(...bytes.subarray(i, i + CHUNK)))
  }
  return btoa(parts.join(''))
}

async function uploadOne(
  prediction: PredictionResult,
  anonymousId: string,
  logger: Logger,
): Promise<void> {
  const filename = prediction.image_path.replace(/\\/g, '/').split('/').pop() ?? ''
  const ext = ('.' + filename.split('.').pop()).toLowerCase()
  const mime = EXT_TO_MIME[ext]

  if (!mime) {
    logger.warn(`[contribution] Skipping unsupported file type: ${filename}`)
    return
  }

  // Use server-reported file size (set during inference) to skip large files
  // without reading them into JS memory at all.
  const knownSize: number | undefined = (prediction as any).file_size
  if (knownSize !== undefined && knownSize > MAX_BYTES) {
    logger.warn(
      `[contribution] Skipping ${filename} — too large (${(knownSize / 1024 / 1024).toFixed(1)} MB > 8 MB limit)`,
    )
    return
  }

  let fileBytes: Uint8Array
  try {
    fileBytes = await readBinaryFile(prediction.image_path)
  } catch (err) {
    logger.warn(`[contribution] Could not read file, skipping: ${filename} — ${err}`)
    return
  }

  if (fileBytes.length > MAX_BYTES) {
    logger.warn(
      `[contribution] Skipping ${filename} — too large (${(fileBytes.length / 1024 / 1024).toFixed(1)} MB > 8 MB limit)`,
    )
    return
  }

  logger.log(
    `[contribution] Uploading ${filename} (${(fileBytes.length / 1024).toFixed(1)} KB) → ${COLLECTION_URL}`,
  )

  const phenotypes = sanitizeFloats(
    prediction.extra_pred_fields?.phenotypes?.map(p => ({
      name: p.name,
      value_px: p.value_px,
    })) ?? []
  )

  const response = await tauriFetch(COLLECTION_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    responseType: ResponseType.Text,
    body: Body.json({
      anonymous_id: anonymousId,
      app_version: APP_VERSION,
      model_version: 'cavfish_v1',
      timestamp: new Date().toISOString(),
      image_filename: filename,
      image_base64: toBase64(fileBytes),
      image_mime: mime,
      keypoints: sanitizeFloats(prediction.keypoints),
      keypoint_scores: sanitizeFloats(prediction.keypoint_scores),
      phenotypes,
    }),
    timeout: 60,
  })

  if (response.ok) {
    logger.log(`[contribution] ✓ Accepted (HTTP ${response.status}): ${filename}`)
  } else {
    logger.warn(
      `[contribution] Server rejected (HTTP ${response.status}): ${filename} — ${response.data}`,
    )
  }
}

/**
 * Upload all predictions sequentially (one at a time) in a background task.
 * Files > 8 MB are skipped. Errors per image are logged and never affect the UI.
 */
export function uploadContributions(
  predictions: PredictionResult[],
  anonymousId: string,
  logger: Logger,
): void {
  void (async () => {
    logger.log(`[contribution] Starting upload of ${predictions.length} image(s)`)
    let ok = 0
    for (const pred of predictions) {
      try {
        await uploadOne(pred, anonymousId, logger)
        ok++
      } catch (err) {
        logger.warn(`[contribution] Upload failed: ${err}`)
      }
    }
    logger.log(`[contribution] Done — ${ok}/${predictions.length} uploaded`)
  })()
}

