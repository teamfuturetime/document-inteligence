import js from '@eslint/js'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {ignores: ['dist/**', 'node_modules/**', '.npm-cache/**']},
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    rules: {
      'no-empty': ['error', {allowEmptyCatch: true}],
      '@typescript-eslint/no-unused-expressions': ['error', {allowTernary: true}],
    },
  },
)
