import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    root: '.',
    build: {
      outDir: '../static',
      emptyOutDir: false, // 保留静态目录中的其他文件
      rollupOptions: {
        output: {
          entryFileNames: `assets/[name].js`,
          chunkFileNames: `assets/[name].js`,
          assetFileNames: `assets/[name].[ext]`
        }
      },
      // 确保构建后的资源引用路径正确
      assetsInlineLimit: 0, // 不内联任何资源，全部作为独立文件
      cssCodeSplit: false, // 不拆分CSS，保持单一文件便于处理
    },
    server: {
      port: 3001, // 修改端口避免与Next.js冲突
      host: '0.0.0.0', // 允许外部访问
      proxy: {
        '/llm-manager': {
          target: 'http://localhost:8200',
          changeOrigin: true,
          secure: false
        }
      }
    },
    // Dev mode: 需要 publicDir 提供 scripts/ shared/ 静态文件
    // Build mode: publicDir 会覆盖已编译的 index.html，需要禁用
    publicDir: mode === 'production' ? false : '.',
    // 确保静态资源能被正确访问
    assetsInclude: ['**/*.html'],
    css: {
      postcss: {
        plugins: [
          require('tailwindcss'),
          require('autoprefixer')
        ]
      }
    },
    plugins: [
      {
        name: 'watch-and-rebuild',
        configureServer(server) {
          // 启动时执行一次完整构建
          setTimeout(() => {
            server.ws.send({ type: 'full-reload' })
          }, 1000)
          
          // 提示用户文件同步服务已启动
          console.log('\n✅ Vite热更新服务已启动')
          console.log('✅ 修改将自动同步到静态目录')
          console.log('📝 开发地址: http://localhost:3000')
          console.log('🌐 静态页面: http://localhost:8200/llm-manager')
          console.log('')
        }
      }
    ],
    
    // 定义全局常量，解决__DEFINES__未定义错误
    define: {
      __DEFINES__: JSON.stringify({}),
      __VUE_OPTIONS_API__: JSON.stringify(true),
      __VUE_PROD_DEVTOOLS__: JSON.stringify(false),
      // 可以根据需要添加更多全局变量定义
    }
  }
})