/**
 * 封面 URL 工具。
 *
 * 后端 /api/bangumi/{id}/cover 支持 ?w= 参数返回按宽度缩放的缩略图。
 * 列表/卡片里的封面只有 200px 左右，直接让浏览器缩小 1200px 原图时，
 * 细线条容易被采样成很硬的深色描边（看起来像黑线），所以按显示宽度取小图。
 */
export function coverThumb(cover: string | null | undefined, width: number): string {
  if (!cover) return '/placeholder.png'
  return `${cover}${cover.includes('?') ? '&' : '?'}w=${width}`
}

/** 卡片封面在 1x / 2x 屏幕下的 srcset，交由浏览器按 DPR 选择合适尺寸。 */
export function coverSrcset(cover: string | null | undefined): string {
  if (!cover) return ''
  return `${coverThumb(cover, 320)} 1x, ${coverThumb(cover, 640)} 2x`
}
