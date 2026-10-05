import { readFile, writeFile } from 'node:fs/promises';
import openapiTS, { astToString } from 'openapi-typescript';

const source = new URL('../../contracts/generated/openapi.json', import.meta.url);
const output = new URL('../src/lib/api.generated.ts', import.meta.url);
const expected = astToString(await openapiTS(source));
if (process.argv.includes('--check')) {
  const actual = await readFile(output, 'utf8').catch(() => '');
  if (actual !== expected) {
    console.error('Frontend contract drift: chạy npm run contracts:generate.');
    process.exitCode = 1;
  } else console.log('Frontend contracts CHECK PASS');
} else {
  await writeFile(output, expected, 'utf8');
  console.log('Frontend contracts generated');
}
