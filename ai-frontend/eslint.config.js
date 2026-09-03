// 前端静态检查配置：适用于 Vue 单文件组件、JavaScript 源码和 Vite 配置。
import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  // 不检查依赖、构建结果和独立演示目录；当前主应用入口为 src/。
  {
    ignores: ['node_modules/**', 'dist/**', 'vue-demo/**'],
  },
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['src/**/*.{js,vue}', 'vite.config.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      // 同时允许浏览器 API（Vue 页面）和 Node.js API（Vite 配置）。
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // 现有页面中存在单词组件名，迁移期间不将该命名习惯作为构建阻断项。
      'vue/multi-word-component-names': 'off',
      // 调试输出由业务代码逐步清理；本次先不因历史 console 语句阻断构建。
      'no-console': 'off',
    },
  },
  // 放在最后，关闭与 Prettier 格式化职责重叠的 ESLint 规则。
  prettier,
]
