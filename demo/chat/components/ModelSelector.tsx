import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Settings, Info } from "lucide-react";
import { getApiUrl, authFetch } from "@/lib/config";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

// localStorage key for persisting selected model config
const STORAGE_KEY = "creditwise_selected_model_config_id";

// 与后端API响应匹配的模型配置接口
interface ModelConfig {
  id: number;
  name: string;
  type: string;
  models: string;
  has_model_config: boolean;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  system_prompt?: string;
  enable_web_search?: boolean;
  enable_deep_thinking?: boolean;
  thinking_budget?: number;
  include_thoughts?: boolean;
}

interface ModelSelectorProps {
  selectedConfig: ModelConfig | null;
  onConfigChange: (config: ModelConfig) => void;
}

export default function ModelSelector({ selectedConfig, onConfigChange }: ModelSelectorProps) {
  const [configs, setConfigs] = useState<ModelConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // 加载模型配置
  const loadConfigs = async () => {
    try {
      setIsLoading(true);
      // 使用统一的 API URL 构造函数
      const response = await authFetch(getApiUrl('/llm-manager/api/manage/channels/active-configs'));
      if (!response.ok) throw new Error('Failed to fetch model configs');
      
      const result = await response.json();
      // API返回格式: { code: 0, data: [...], message: "..." }
      const configList = result.data || [];
      setConfigs(configList);
      
      // 尝试从localStorage恢复上次选择的配置
      const savedConfigId = localStorage.getItem(STORAGE_KEY);
      if (savedConfigId && configList.length > 0) {
        const savedConfig = configList.find((c: ModelConfig) => c.id.toString() === savedConfigId);
        if (savedConfig) {
          onConfigChange(savedConfig);
          return;
        }
      }
      
      // 如果没有保存的配置或保存的配置不存在，选择第一个
      if (configList.length > 0) {
        onConfigChange(configList[0]);
      }
    } catch (error) {
      console.error('Failed to load model configs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, []);

  const handleConfigSelect = (configId: string) => {
    const config = configs.find(c => c.id.toString() === configId);
    if (config) {
      // 保存选择到localStorage
      localStorage.setItem(STORAGE_KEY, configId);
      onConfigChange(config);
    }
  };

  // 获取模型名称（从models字段解析第一个模型）
  const getModelName = (models: string) => {
    if (!models) return "未知模型";
    const modelList = models.split(",").map(m => m.trim());
    return modelList[0] || "未知模型";
  };

  // 获取模型列表
  const getModelList = (models: string) => {
    if (!models) return [];
    return models.split(",").map(m => m.trim()).filter(m => m);
  };

  return (
    <div className="w-full">
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <Select
            value={selectedConfig?.id?.toString() || ""}
            onValueChange={handleConfigSelect}
            disabled={isLoading || configs.length === 0}
          >
            <SelectTrigger className="w-full h-9">
              <SelectValue placeholder={isLoading ? "加载中..." : configs.length === 0 ? "无可用配置" : "选择模型配置"} />
            </SelectTrigger>
            <SelectContent>
              {configs.map((config) => (
                <SelectItem key={config.id} value={config.id.toString()}>
                  <div className="flex flex-col items-start">
                    <div className="font-medium">{config.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {config.type} · {getModelName(config.models)}
                    </div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {selectedConfig && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="sm" className="h-9 w-9 p-0">
                  <Info className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1 text-xs">
                  <div>渠道: {selectedConfig.type}</div>
                  <div>模型: {getModelName(selectedConfig.models)}</div>
                  {selectedConfig.has_model_config && (
                    <>
                      <div>温度: {selectedConfig.temperature ?? "默认"}</div>
                      <div>最大令牌: {selectedConfig.max_tokens ?? "默认"}</div>
                    </>
                  )}
                  {!selectedConfig.has_model_config && (
                    <div className="text-yellow-500">使用默认参数</div>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
}