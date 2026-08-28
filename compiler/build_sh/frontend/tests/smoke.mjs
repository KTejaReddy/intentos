// Generated frontend smoke test: assert the build output exists.
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const dist = join(process.cwd(), 'dist')
const idx = join(dist, 'index.html')
if (!existsSync(idx)) {
  console.error('dist/index.html missing — run npm run build first')
  process.exit(1)
}
const html = readFileSync(idx, 'utf-8')
console.log(`frontend smoke: index.html ${html.length} bytes`)
if (!existsSync(join(dist, 'assets'))) { console.warn('assets dir missing') }
if (!existsSync(join(dist, 'assets'))) { console.warn('assets dir missing') }