import { useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes } from 'react-router-dom';
import { Alert, Card, ConfigProvider, Descriptions, Empty, Layout, Space, Spin, Typography } from 'antd';
import { get, type Health, type Capabilities } from '../api/client';
function Overview() {
  const [data, setData] = useState<[Health, Capabilities]>();
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([get<Health>('/health', controller.signal), get<Capabilities>('/capabilities', controller.signal)])
      .then(setData).catch((e: Error) => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, []);
  if (error) return <Alert type="error" message="后端连接失败" description={error} showIcon />;
  if (!data) return <Spin tip="正在读取服务状态"><div style={{ height: 120 }} /></Spin>;
  const [health, capabilities] = data;
  return <Space direction="vertical" size="large" style={{ width: '100%' }}>
    <Alert type="info" showIcon message={`当前 AI 配置：${capabilities.ai_provider}${capabilities.is_simulated ? '（模拟配置）' : ''}`} description="S01 仅完成工程骨架。AI、解析、OCR 与业务任务尚未实现。" />
    <Card title="服务状态"><Descriptions column={1} items={[{ key: 'health', label: '健康', children: `${health.status} · v${health.version}` }, ...Object.entries(capabilities).filter(([key]) => !['ai_provider', 'is_simulated'].includes(key)).map(([key, value]) => ({ key, label: key, children: String(value) }))]} /></Card>
  </Space>;
}
export default function App() {
  return <ConfigProvider><Layout style={{ minHeight: '100vh' }}><Layout.Header><Typography.Text style={{ color: 'white', fontSize: 20 }}>智标 AI · 材料核验</Typography.Text></Layout.Header><Layout.Content style={{ padding: '32px', maxWidth: 1100, width: '100%', margin: '0 auto', boxSizing: 'border-box' }}><Space size="large" style={{ marginBottom: 24 }}><Link to="/">服务概览</Link><Link to="/projects">项目</Link></Space><Routes><Route path="/" element={<Overview />} /><Route path="/projects" element={<Card title="项目工作区"><Empty description="S02 已提供后端项目接口，当前工作台尚未接入项目数据" /></Card>} /><Route path="*" element={<Navigate to="/" replace />} /></Routes></Layout.Content></Layout></ConfigProvider>;
}
