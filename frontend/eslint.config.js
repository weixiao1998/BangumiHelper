import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'

export default [
  {
    ignores: ['**/dist/**', '**/node_modules/**', '*.d.ts'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
  },
  {
    rules: {
      // TS 编译器已承担未定义变量检查；unplugin-auto-import 会注入全局（如 ElMessage），避免误报
      'no-undef': 'off',
      'no-use-before-define': 'off',
      'no-empty': ['error', { allowEmptyCatch: true }],
      // 路由视图组件多是单字命名（Calendar/Login...），这是命名习惯，不必强行 multi-word
      'vue/multi-word-component-names': 'off',
    },
  },
]
