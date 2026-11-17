export type Health = { status: 'ok'; version: string; timestamp: string };
export type CapabilityState = 'available' | 'unavailable' | 'not_configured' | 'unknown';
export type Capabilities = { ai_provider: 'mock' | 'haier_workflow' | 'internal_model'; is_simulated: boolean } & Record<'parser_pdf' | 'ocr' | 'word_converter' | 'storage' | 'database' | 'workflow_api', CapabilityState>;
const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '');
export async function get<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${base}${path}`, { signal });
  if (!response.ok) throw new Error(`服务请求失败（HTTP ${response.status}）`);
  return response.json() as Promise<T>;
}
