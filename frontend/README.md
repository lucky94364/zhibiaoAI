# frontend

S01：React/TypeScript/Vite/Ant Design 工程；服务概览读取真实 health 与 capabilities，项目路由仅说明后续功能，没有模拟项目数据。

验证环境 Node 22.19.0、npm 10.9.3；Node 要求 >=22.12 且 <23。准确依赖版本见 package-lock.json。

```sh
cd frontend
npm ci
npm run dev
npm run typecheck
npm run build
npm run preview
```

开发地址 http://127.0.0.1:5173（固定端口），默认 `/api` 代理至 http://127.0.0.1:8000。本次 8000 被占用，后端使用 8001，启动命令为：

```sh
ZB_DEV_API_TARGET=http://127.0.0.1:8001 npm run dev
```

可在 frontend/.env.local 配置公开的 `VITE_API_BASE_URL`（默认 /api/v1）；跨域地址需与后端 CORS 匹配。前端不读取根 .env，不放密钥。生产构建需要托管端配置 /api 反向代理和 SPA 路由回退，本阶段未部署。

验证包含类型检查、生产构建、开发服务 HTML 与代理实际 HTTP 联通。尚未执行浏览器视觉或端到端测试。Ant Design 单包构建有 >500kB 提示，后续工作台阶段按页面拆包。
