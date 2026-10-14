import { createHash } from 'node:crypto'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { compile } from 'json-schema-to-typescript'

const source = new URL('../../schemas/v1/', import.meta.url)
const output = new URL('../src/api/generated/', import.meta.url)
const check = process.argv.includes('--check')
const files = (await readdir(source)).filter(name => name.endsWith('.schema.json')).sort()
if (!check) await mkdir(output, { recursive: true })
for (const name of files) {
  const text = await readFile(new URL(name, source), 'utf8')
  const schema = JSON.parse(text)
  const hash = createHash('sha256').update(text).digest('hex')
  const result = await compile(schema, schema.title, {
    cwd: fileURLToPath(source),
    bannerComment: `/* Generated from schemas/v1/${name}. Do not edit.\n * Source SHA-256: ${hash}\n */`,
  })
  const target = new URL(name.replace('.schema.json', '.d.ts'), output)
  if (check) {
    const actual = await readFile(target, 'utf8').catch(() => '')
    if (actual !== result) throw new Error(`Contract drift: ${name}; run npm run contracts:generate`)
  } else {
    await writeFile(target, result)
  }
}
console.log(`${check ? 'Checked' : 'Generated'} ${files.length} TypeScript contracts`)
