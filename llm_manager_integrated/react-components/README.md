# LLM API Manager React Components

可集成到任何React应用的LLM API管理组件库

## 安装

```bash
npm install llm-api-manager-react-components
# 或者
yarn add llm-api-manager-react-components
```

## 基本使用

### 1. 设置提供者

在您的应用根组件中包装LLMManagerProvider：

```jsx
import React from 'react';
import { LLMManagerProvider } from 'llm-api-manager-react-components';

function App() {
  return (
    <LLMManagerProvider
      headers={{
        'Authorization': 'Bearer your-token'
      }}
      theme={{
        primaryColor: '#007bff',
        successColor: '#28a745',
        dangerColor: '#dc3545'
      }}
    >
      {/* 您的应用内容 */}
    </LLMManagerProvider>
  );
}
```

### 2. 使用组件

```jsx
import React from 'react';
import { ChannelManager, APILogs, Statistics } from 'llm-api-manager-react-components';

function Dashboard() {
  return (
    <div>
      <ChannelManager 
        apiEndpoint="/api/llm-manager/channels"
        onChannelSelect={(channel) => console.log(channel)}
      />
      
      <APILogs 
        apiEndpoint="/api/llm-manager/logs"
      />
      
      <Statistics 
        apiEndpoint="/api/llm-manager/stats"
      />
    </div>
  );
}
```

## 组件API

### ChannelManager

渠道管理组件

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| apiEndpoint | string | '/api/manage/channels' | API端点 |
| headers | object | {} | 请求头 |
| onChannelSelect | function | - | 渠道选择回调 |
| showActions | boolean | true | 是否显示操作按钮 |
| customStyles | object | {} | 自定义样式 |
| theme | object | {} | 主题配置 |
| selectable | boolean | false | 是否可选择渠道 |
| onApiError | function | - | API错误回调 |

#### 示例

```jsx
<ChannelManager 
  apiEndpoint="/api/llm-manager/channels"
  headers={{
    'Authorization': 'Bearer your-token'
  }}
  selectable={true}
  onChannelSelect={(channel) => {
    // 处理渠道选择
    console.log('Selected:', channel);
  }}
  customStyles={{
    container: {
      backgroundColor: '#f8f9fa'
    }
  }}
/>
```

### APILogs

API调用日志组件

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| apiEndpoint | string | '/api/logs' | API端点 |
| headers | object | {} | 请求头 |
| customStyles | object | {} | 自定义样式 |
| theme | object | {} | 主题配置 |
| showFilters | boolean | true | 是否显示过滤器 |
| onApiError | function | - | API错误回调 |
| pageSize | number | 20 | 每页显示数量 |

#### 示例

```jsx
<APILogs 
  apiEndpoint="/api/llm-manager/logs"
  showFilters={true}
  pageSize={50}
  onApiError={(error) => {
    console.error('API错误:', error);
  }}
/>
```

### Statistics

统计分析组件

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| apiEndpoint | string | '/api/logs/stats' | API端点 |
| headers | object | {} | 请求头 |
| customStyles | object | {} | 自定义样式 |
| theme | object | {} | 主题配置 |
| showFilters | boolean | true | 是否显示过滤器 |
| onApiError | function | - | API错误回调 |

#### 示例

```jsx
<Statistics 
  apiEndpoint="/api/llm-manager/stats"
  showFilters={true}
  theme={{
    primaryColor: '#6f42c1'
  }}
/>
```

## 钩子函数

### useApiData

获取API数据的钩子

```jsx
import { useApiData } from 'llm-api-manager-react-components';

function MyComponent() {
  const { data, loading, error, refetch } = useApiData('/api/channels', {
    params: { limit: 10 },
    deps: [], // 依赖变化时重新获取数据
    immediate: true, // 是否立即获取数据
    transform: data => data.map(item => ({ ...item, active: false })) // 数据转换
  });
  
  if (loading) return <div>加载中...</div>;
  if (error) return <div>错误: {error}</div>;
  
  return (
    <div>
      {data?.map(channel => (
        <div key={channel.id}>{channel.name}</div>
      ))}
    </div>
  );
}
```

### useApiAction

执行API操作的钩子

```jsx
import { useApiAction } from 'llm-api-manager-react-components';

function MyComponent() {
  const { execute, loading, error } = useApiAction();
  
  const handleDelete = async (id) => {
    try {
      const result = await execute('DELETE', `/api/channels/${id}`);
      console.log('删除成功:', result);
    } catch (err) {
      console.error('删除失败:', err);
    }
  };
  
  return (
    <button onClick={() => handleDelete(1)} disabled={loading}>
      {loading ? '删除中...' : '删除'}
    </button>
  );
}
```

### useNotification

使用通知的钩子

```jsx
import { useNotification } from 'llm-api-manager-react-components';

function MyComponent() {
  const { addNotification } = useNotification();
  
  const handleSuccess = () => {
    addNotification('success', '操作成功');
  };
  
  const handleError = () => {
    addNotification('error', '操作失败', {
      autoClose: false // 不自动关闭
    });
  };
  
  return (
    <div>
      <button onClick={handleSuccess}>成功</button>
      <button onClick={handleError}>失败</button>
    </div>
  );
}
```

## 主题定制

您可以通过LLMManagerProvider或组件属性自定义主题：

```jsx
const customTheme = {
  primaryColor: '#007bff',
  secondaryColor: '#6c757d',
  successColor: '#28a745',
  dangerColor: '#dc3545',
  warningColor: '#ffc107',
  textColor: '#212529',
  secondaryTextColor: '#6c757d',
  headerBgColor: '#f8f9fa',
  cardBgColor: '#ffffff',
  borderColor: '#dee2e6',
  selectedBgColor: '#e3f2fd',
  detailBgColor: '#f8f9fa'
};

<LLMManagerProvider theme={customTheme}>
  {/* 应用内容 */}
</LLMManagerProvider>
```

## 样式定制

您可以通过customStyles属性自定义组件样式：

```jsx
const customStyles = {
  container: {
    backgroundColor: '#f8f9fa',
    border: '1px solid #dee2e6'
  },
  button: {
    borderRadius: '20px'
  },
  table: {
    fontSize: '14px'
  }
};

<ChannelManager customStyles={customStyles} />
```

## 开发

```bash
# 安装依赖
npm install

# 构建
npm run build

# 运行测试
npm test
```

## 许可证

MIT