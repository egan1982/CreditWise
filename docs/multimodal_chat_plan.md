# AI对话多模态支持功能增强计划

## 文档信息
- **创建日期**: 2025-12-22
- **任务状态**: 待实施
- **优先级**: 中
- **预计工作量**: 1-2天

---

## 一、功能概述

### 1.1 目标
增强Web UI Chat的多模态能力，支持用户通过粘贴、拖拽方式添加图片/文件到对话中，并使用支持多模态的LLM（如GPT-4V、Claude 3、Gemini等）进行任务对话。

### 1.2 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 文件上传按钮 | ✅ 已有 | 点击📎按钮选择文件上传到工作区 |
| 拖拽文件到工作区 | ✅ 已有 | 拖拽到左侧文件树 |
| 右键添加到对话 | ✅ 已有 | 工作区文件右键"添加到AI对话" |
| **粘贴图片到输入框** | ❌ 未实现 | Ctrl+V 粘贴剪贴板图片 |
| **拖拽文件到输入框** | ❌ 未实现 | 拖拽图片/文件到输入区域 |
| **图片预览显示** | ❌ 未实现 | 发送前预览已添加的图片 |
| **多模态消息格式** | ❌ 未实现 | OpenAI Vision API格式支持 |

---

## 二、技术方案

### 2.1 多模态消息格式（OpenAI标准）

```json
{
  "model": "gpt-4-vision-preview",
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "请分析这张图片中的数据趋势" },
        { 
          "type": "image_url", 
          "image_url": { 
            "url": "data:image/png;base64,iVBORw0KGgo...",
            "detail": "auto"
          } 
        }
      ]
    }
  ]
}
```

### 2.2 支持的图片来源

| 来源 | 实现方式 | 数据格式 |
|------|----------|----------|
| 剪贴板粘贴 | `onPaste` 事件 | Base64 Data URL |
| 拖拽图片 | `onDrop` 事件 | Base64 Data URL |
| 本地文件选择 | `<input type="file">` | Base64 Data URL |
| 工作区文件引用 | 右键"添加到AI对话" | 服务端URL或Base64 |

### 2.3 数据结构设计

```typescript
// 图片附件类型
interface ImageAttachment {
  id: string;
  name: string;
  type: 'image';
  mimeType: string;        // image/png, image/jpeg, etc.
  dataUrl: string;         // data:image/png;base64,...
  width?: number;
  height?: number;
  size: number;            // 文件大小（字节）
  source: 'paste' | 'drop' | 'upload' | 'workspace';
}

// 文件附件类型（非图片）
interface FileAttachment {
  id: string;
  name: string;
  type: 'file';
  mimeType: string;
  path?: string;           // 工作区路径（如果来自工作区）
  dataUrl?: string;        // Base64（如果是上传的）
  size: number;
}

// 统一附件类型
type ChatAttachment = ImageAttachment | FileAttachment;

// 多模态消息内容
type MessageContent = string | Array<{
  type: 'text' | 'image_url';
  text?: string;
  image_url?: {
    url: string;
    detail?: 'auto' | 'low' | 'high';
  };
}>;
```

---

## 三、实施计划

### 3.1 阶段一：前端UI增强

#### 3.1.1 创建图片预览组件

**新建文件**: `demo/chat/components/ImageAttachment.tsx`

```typescript
// 功能：
// - 显示图片缩略图
// - 悬停显示原图预览
// - 删除按钮
// - 显示图片尺寸/大小信息
```

#### 3.1.2 输入框增强

**修改文件**: `demo/chat/components/three-panel-interface.tsx`

- [ ] 添加 `imageAttachments` 状态
- [ ] 实现 `onPaste` 事件处理（粘贴图片）
- [ ] 实现 `onDrop` 事件处理（拖拽图片）
- [ ] 实现 `onDragOver` 事件（拖拽视觉反馈）
- [ ] 在输入框上方显示图片预览列表
- [ ] 图片大小限制和格式验证

#### 3.1.3 任务清单

- [ ] 创建 `ImageAttachment.tsx` 组件
- [ ] 创建 `ImageAttachmentList.tsx` 列表组件
- [ ] 添加粘贴事件处理 `handlePaste`
- [ ] 添加拖拽事件处理 `handleDrop`
- [ ] 添加拖拽视觉反馈状态
- [ ] 图片压缩/调整大小工具函数

### 3.2 阶段二：消息格式转换

#### 3.2.1 修改消息发送逻辑

**修改文件**: `demo/chat/components/three-panel-interface.tsx`

```typescript
// 将消息转换为多模态格式
function buildMultimodalMessage(
  text: string, 
  images: ImageAttachment[],
  fileRefs: FileReference[]
): MessageContent {
  if (images.length === 0) {
    // 纯文本消息
    return text + formatFileReferencesForMessage(fileRefs);
  }
  
  // 多模态消息
  const content: MessageContent = [];
  
  // 添加文本
  if (text.trim() || fileRefs.length > 0) {
    content.push({
      type: 'text',
      text: text + formatFileReferencesForMessage(fileRefs)
    });
  }
  
  // 添加图片
  for (const img of images) {
    content.push({
      type: 'image_url',
      image_url: {
        url: img.dataUrl,
        detail: 'auto'
      }
    });
  }
  
  return content;
}
```

#### 3.2.2 任务清单

- [ ] 实现 `buildMultimodalMessage` 函数
- [ ] 修改 `handleSendMessage` 使用新格式
- [ ] 消息历史中正确显示图片
- [ ] 处理AI回复中的图片（如果有）

### 3.3 阶段三：后端适配

#### 3.3.1 Chat API修改

**修改文件**: `API/chat_api.py`

- [ ] 支持接收多模态消息格式
- [ ] 透传多模态内容到LLM服务
- [ ] 处理不支持多模态的模型（降级为纯文本）

#### 3.3.2 渠道客户端适配

**修改文件**: `API/channel_client.py`

- [ ] 检测渠道是否支持多模态
- [ ] 不同提供商的多模态格式转换
  - OpenAI: 原生支持
  - Claude: 需要转换为Anthropic格式
  - Google: 需要转换为Gemini格式

#### 3.3.3 任务清单

- [ ] `chat_api.py` 支持多模态消息解析
- [ ] 添加模型多模态能力检测
- [ ] Claude多模态格式转换
- [ ] Gemini多模态格式转换
- [ ] 不支持多模态时的降级处理

### 3.4 阶段四：优化增强

- [ ] 图片压缩（超过4MB自动压缩）
- [ ] 支持的图片格式验证（PNG/JPEG/GIF/WebP）
- [ ] 多图片上传限制（如最多4张）
- [ ] 图片加载进度显示
- [ ] 错误处理和用户提示
- [ ] 移动端触摸支持

---

## 四、关键代码设计

### 4.1 粘贴事件处理

```typescript
const handlePaste = useCallback((e: React.ClipboardEvent) => {
  const items = e.clipboardData?.items;
  if (!items) return;

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      const file = item.getAsFile();
      if (file) {
        processImageFile(file, 'paste');
      }
      break;
    }
  }
}, []);

const processImageFile = async (file: File, source: ImageAttachment['source']) => {
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    toast({ description: '请选择图片文件', variant: 'destructive' });
    return;
  }

  // 验证文件大小（20MB限制）
  const MAX_SIZE = 20 * 1024 * 1024;
  if (file.size > MAX_SIZE) {
    toast({ description: '图片大小不能超过20MB', variant: 'destructive' });
    return;
  }

  // 读取为Base64
  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUrl = e.target?.result as string;
    
    // 获取图片尺寸
    const img = new Image();
    img.onload = () => {
      const attachment: ImageAttachment = {
        id: `img-${Date.now()}`,
        name: file.name || `image-${Date.now()}.png`,
        type: 'image',
        mimeType: file.type,
        dataUrl,
        width: img.width,
        height: img.height,
        size: file.size,
        source,
      };
      
      setImageAttachments(prev => [...prev, attachment]);
      toast({ description: `已添加图片: ${attachment.name}` });
    };
    img.src = dataUrl;
  };
  reader.readAsDataURL(file);
};
```

### 4.2 拖拽事件处理

```typescript
const [isDragOver, setIsDragOver] = useState(false);

const handleDragOver = useCallback((e: React.DragEvent) => {
  e.preventDefault();
  e.stopPropagation();
  
  // 检查是否包含图片
  const hasImage = Array.from(e.dataTransfer.types).some(
    type => type === 'Files' || type.startsWith('image/')
  );
  
  if (hasImage) {
    setIsDragOver(true);
    e.dataTransfer.dropEffect = 'copy';
  }
}, []);

const handleDragLeave = useCallback((e: React.DragEvent) => {
  e.preventDefault();
  e.stopPropagation();
  setIsDragOver(false);
}, []);

const handleDrop = useCallback((e: React.DragEvent) => {
  e.preventDefault();
  e.stopPropagation();
  setIsDragOver(false);

  const files = e.dataTransfer.files;
  for (const file of files) {
    if (file.type.startsWith('image/')) {
      processImageFile(file, 'drop');
    }
  }
}, []);
```

### 4.3 图片预览组件

```tsx
// ImageAttachment.tsx
interface ImageAttachmentProps {
  attachment: ImageAttachment;
  onRemove: (id: string) => void;
}

export function ImageAttachmentPreview({ attachment, onRemove }: ImageAttachmentProps) {
  return (
    <div className="relative group">
      <img
        src={attachment.dataUrl}
        alt={attachment.name}
        className="h-16 w-16 object-cover rounded-md border border-gray-200 dark:border-gray-700"
      />
      <button
        onClick={() => onRemove(attachment.id)}
        className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <X className="w-3 h-3" />
      </button>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs px-1 truncate">
            {attachment.name}
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>{attachment.name}</p>
          <p>{attachment.width}x{attachment.height}</p>
          <p>{formatFileSize(attachment.size)}</p>
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
```

### 4.4 Claude多模态格式转换

```python
# channel_client.py
def convert_to_anthropic_format(messages: List[Dict]) -> List[Dict]:
    """将OpenAI多模态格式转换为Anthropic格式"""
    converted = []
    for msg in messages:
        content = msg.get('content')
        
        if isinstance(content, str):
            # 纯文本消息
            converted.append(msg)
        elif isinstance(content, list):
            # 多模态消息
            anthropic_content = []
            for item in content:
                if item['type'] == 'text':
                    anthropic_content.append({
                        'type': 'text',
                        'text': item['text']
                    })
                elif item['type'] == 'image_url':
                    url = item['image_url']['url']
                    if url.startswith('data:'):
                        # Base64图片
                        media_type, base64_data = parse_data_url(url)
                        anthropic_content.append({
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': media_type,
                                'data': base64_data
                            }
                        })
            converted.append({
                'role': msg['role'],
                'content': anthropic_content
            })
    
    return converted
```

---

## 五、UI设计

### 5.1 输入区域布局

```
┌─────────────────────────────────────────────────────────────────┐
│  引用文件: [📄 train.csv ✕]                                      │
├─────────────────────────────────────────────────────────────────┤
│  图片: [🖼️ ✕] [🖼️ ✕] [🖼️ ✕]  ← 图片缩略图，悬停显示大图        │
├─────────────────────────────────────────────────────────────────┤
│  [模型选择器: GPT-4 Vision ▼]                                   │
│  [📎] [🖼️] [请分析这张图表中的数据趋势...          ] [发送]     │
│                                                                  │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│  │         拖拽图片到此处或 Ctrl+V 粘贴           │   │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│                    ↑ 拖拽时显示的虚线区域                        │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 消息气泡中的图片显示

```
┌─────────────────────────────────────────┐
│ 👤 用户                                  │
│                                          │
│ 请分析这张图表中的数据趋势               │
│                                          │
│ ┌──────────┐ ┌──────────┐               │
│ │  图片1   │ │  图片2   │  ← 点击放大   │
│ └──────────┘ └──────────┘               │
│                                          │
│ 📎 引用文件:                             │
│ • train.csv                              │
└─────────────────────────────────────────┘
```

---

## 六、兼容性考虑

### 6.1 模型多模态支持情况

| 提供商 | 模型 | 多模态支持 | 备注 |
|--------|------|-----------|------|
| OpenAI | gpt-4-vision-preview | ✅ | 原生支持 |
| OpenAI | gpt-4o | ✅ | 原生支持 |
| OpenAI | gpt-4o-mini | ✅ | 原生支持 |
| OpenAI | gpt-3.5-turbo | ❌ | 不支持 |
| Anthropic | claude-3-opus | ✅ | 需格式转换 |
| Anthropic | claude-3-sonnet | ✅ | 需格式转换 |
| Anthropic | claude-3-haiku | ✅ | 需格式转换 |
| Google | gemini-pro-vision | ✅ | 需格式转换 |
| DeepSeek | deepseek-chat | ❌ | 不支持 |
| DeepSeek | deepseek-vl | ✅ | 需确认格式 |

### 6.2 模型多模态支持检测策略

#### 6.2.1 问题分析

| 场景 | LLM服务商行为 | 风险 |
|------|--------------|------|
| 已知不支持多模态的模型 | 返回400错误（如OpenAI/Anthropic） | 用户体验差（发送后才报错） |
| 未知模型 | **可能静默忽略图片**，只处理文本 | ❌ **最危险**：用户以为AI看到了图片 |
| 本地部署模型 | 行为不确定 | 需要测试确认 |

**核心问题**：不能完全依赖后端错误，因为部分模型不会报错而是静默忽略图片内容。

#### 6.2.2 推荐方案：混合检测

```typescript
// 前端模型多模态支持检测
const KNOWN_MULTIMODAL_MODELS = [
  'gpt-4-vision', 'gpt-4o', 'gpt-4o-mini',
  'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku', 'claude-3.5-sonnet',
  'gemini-pro-vision', 'gemini-1.5-pro', 'gemini-2.0',
  'deepseek-vl',
];

const KNOWN_TEXT_ONLY_MODELS = [
  'gpt-3.5-turbo', 'gpt-4-turbo',
  'deepseek-chat', 'deepseek-coder', 'deepseek-reasoner',
  'claude-2', 'claude-instant',
];

type MultimodalSupport = 'supported' | 'unsupported' | 'unknown';

function checkMultimodalSupport(modelId: string): MultimodalSupport {
  const lowerModelId = modelId.toLowerCase();
  if (KNOWN_MULTIMODAL_MODELS.some(m => lowerModelId.includes(m))) return 'supported';
  if (KNOWN_TEXT_ONLY_MODELS.some(m => lowerModelId.includes(m))) return 'unsupported';
  return 'unknown';
}
```

#### 6.2.3 前端发送前检测逻辑

```typescript
function handleSendWithImages(modelId: string, images: ImageAttachment[]): boolean {
  if (images.length === 0) return true;  // 无图片，直接发送
  
  const support = checkMultimodalSupport(modelId);
  
  switch (support) {
    case 'unsupported':
      // 已知不支持 → 明确拦截
      toast.error(`模型 ${modelId} 不支持图片输入，请切换到支持视觉的模型（如 GPT-4o、Claude 3）`);
      return false;
      
    case 'unknown':
      // 未知模型 → 警告但允许尝试，依赖后端错误处理
      toast.warning(`模型 ${modelId} 的图片支持情况未知，将尝试发送。如果模型不支持，图片可能被忽略。`);
      return true;
      
    case 'supported':
    default:
      return true;
  }
}
```

#### 6.2.4 后端错误友好化

```python
# chat_api.py - 捕获多模态相关错误并友好化
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    try:
        response = await channel_client.chat(request)
        return response
    except Exception as e:
        error_msg = str(e).lower()
        
        # 检测多模态相关错误关键词
        multimodal_keywords = ['image', 'vision', 'multimodal', 'content array', 'not support']
        if any(kw in error_msg for kw in multimodal_keywords):
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "model_not_support_multimodal",
                        "message": "当前模型不支持图片输入，请切换到支持视觉的模型（如 GPT-4o、Claude 3）"
                    }
                }
            )
        raise

#### 6.2.5 方案优势

| 层级 | 处理内容 | 用户体验 |
|------|----------|----------|
| **前端白名单** | 已知支持/不支持的模型 | ✅ 提前拦截，体验最好 |
| **前端警告** | 未知模型 | ⚠️ 警告用户风险 |
| **后端兜底** | 捕获LLM返回的错误 | 🔄 最后防线，友好化错误信息 |

### 6.3 降级策略

当检测到模型不支持多模态时：
1. **已知不支持**：显示错误提示，阻止发送，建议切换模型
2. **未知模型**：显示警告，允许尝试发送，依赖后端错误处理
3. **后端报错**：友好化错误信息，提示用户切换模型

---

## 七、测试计划

### 7.1 功能测试

- [ ] 粘贴PNG图片
- [ ] 粘贴JPEG图片
- [ ] 粘贴截图
- [ ] 拖拽单张图片
- [ ] 拖拽多张图片
- [ ] 拖拽非图片文件（应拒绝或提示）
- [ ] 超大图片处理（>20MB）
- [ ] 多图片+文本混合发送
- [ ] 图片+文件引用混合发送

### 7.2 兼容性测试

- [ ] OpenAI GPT-4V
- [ ] Claude 3 Sonnet
- [ ] 不支持多模态的模型降级

### 7.3 边界测试

- [ ] 空消息只有图片
- [ ] 连续发送多条图片消息
- [ ] 网络中断时的图片上传
- [ ] 浏览器兼容性（Chrome/Firefox/Safari）

---

## 八、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 大图片导致请求超时 | 发送失败 | 自动压缩超过4MB的图片 |
| Base64编码增大请求体 | 性能下降 | 考虑先上传到服务器再引用URL |
| 不同LLM格式不兼容 | 调用失败 | 后端统一格式转换层 |
| 移动端粘贴不支持 | 功能缺失 | 提供文件选择按钮作为备选 |
| **模型静默忽略图片** | **用户误以为AI看到图片** | **前端白名单检测 + 未知模型警告** |

---

## 九、参考资源

- [OpenAI Vision API文档](https://platform.openai.com/docs/guides/vision)
- [Anthropic Claude Vision文档](https://docs.anthropic.com/claude/docs/vision)
- [Google Gemini Vision文档](https://ai.google.dev/tutorials/image_prompting)

---

## 十、更新日志

| 日期 | 更新内容 | 操作人 |
|------|----------|--------|
| 2025-12-22 | 创建计划文档 | AI |
| 2026-02-06 | 新增6.2模型多模态支持检测策略（混合检测方案：前端白名单+后端兜底） | AI |
