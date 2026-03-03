import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

interface ModelConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  channelId: string;
}

interface Channel {
  id: string;
  name: string;
  type: string;
  provider_id: string;
  is_active: boolean;
}

interface ModelProvider {
  id: string;
  name: string;
  type: string;
  supported_models: string[];
}

export default function ModelConfigModal({ isOpen, onClose, channelId }: ModelConfigModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [channel, setChannel] = useState<Channel | null>(null);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [configName, setConfigName] = useState("");
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [temperature, setTemperature] = useState([0.7]);
  const [maxTokens, setMaxTokens] = useState([4096]);
  const [topP, setTopP] = useState([1.0]);
  const [frequencyPenalty, setFrequencyPenalty] = useState([0]);
  const [presencePenalty, setPresencePenalty] = useState([0]);
  const [isActive, setIsActive] = useState(true);

  // 加载渠道信息
  const loadChannel = async () => {
    if (!channelId) return;
    
    try {
      setIsLoading(true);
      const response = await fetch(`/llm-manager/api/channels/${channelId}`);
      if (!response.ok) throw new Error('Failed to fetch channel');
      
      const data = await response.json();
      setChannel(data);
    } catch (error) {
      console.error('Failed to load channel:', error);
      toast({
        description: "加载渠道信息失败",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 加载提供商列表
  const loadProviders = async () => {
    try {
      const response = await fetch('/llm-manager/api/providers');
      if (!response.ok) throw new Error('Failed to fetch providers');
      
      const data = await response.json();
      setProviders(data.providers || []);
      
      // 默认选择第一个提供商
      if (data.providers && data.providers.length > 0) {
        setSelectedProviderId(data.providers[0].id);
        if (data.providers[0].supported_models && data.providers[0].supported_models.length > 0) {
          setSelectedModel(data.providers[0].supported_models[0]);
        }
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
      toast({
        description: "加载提供商列表失败",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadChannel();
      loadProviders();
      // 重置表单
      setConfigName("");
      setSelectedProviderId("");
      setSelectedModel("");
      setTemperature([0.7]);
      setMaxTokens([4096]);
      setTopP([1.0]);
      setFrequencyPenalty([0]);
      setPresencePenalty([0]);
      setIsActive(true);
    }
  }, [isOpen, channelId]);

  // 保存配置
  const handleSave = async () => {
    if (!configName.trim() || !selectedProviderId || !selectedModel) {
      toast({
        description: "请填写所有必填字段",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsSaving(true);
      
      const configData = {
        name: configName.trim(),
        channel_id: channelId,
        provider_id: selectedProviderId,
        model_name: selectedModel,
        models: [selectedModel], // 简化处理，只使用单个模型
        temperature: temperature[0],
        max_tokens: maxTokens[0],
        top_p: topP[0],
        frequency_penalty: frequencyPenalty[0],
        presence_penalty: presencePenalty[0],
        is_active: isActive
      };

      const response = await fetch('/llm-manager/api/model-configs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(configData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save config');
      }

      toast({
        description: "模型配置已保存",
      });
      onClose();
      
      // 触发父组件重新加载
      window.location.reload();
    } catch (error) {
      console.error('Failed to save config:', error);
      toast({
        description: error instanceof Error ? error.message : "保存配置失败",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const selectedProvider = providers.find(p => p.id === selectedProviderId);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>创建模型配置</DialogTitle>
        </DialogHeader>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span className="ml-2">加载中...</span>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="configName">配置名称</Label>
              <Input
                id="configName"
                placeholder="输入配置名称"
                value={configName}
                onChange={(e) => setConfigName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider">提供商</Label>
              <Select value={selectedProviderId} onValueChange={setSelectedProviderId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择提供商" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((provider) => (
                    <SelectItem key={provider.id} value={provider.id}>
                      {provider.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="model">模型</Label>
              <Select 
                value={selectedModel} 
                onValueChange={setSelectedModel}
                disabled={!selectedProvider}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择模型" />
                </SelectTrigger>
                <SelectContent>
                  {selectedProvider?.supported_models.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>温度: {temperature[0]}</Label>
              <Slider
                value={temperature}
                onValueChange={setTemperature}
                max={2}
                min={0}
                step={0.1}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label>最大令牌数: {maxTokens[0]}</Label>
              <Slider
                value={maxTokens}
                onValueChange={setMaxTokens}
                max={8192}
                min={1}
                step={128}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label>Top P: {topP[0]}</Label>
              <Slider
                value={topP}
                onValueChange={setTopP}
                max={1}
                min={0}
                step={0.1}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label>频率惩罚: {frequencyPenalty[0]}</Label>
              <Slider
                value={frequencyPenalty}
                onValueChange={setFrequencyPenalty}
                max={2}
                min={0}
                step={0.1}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <Label>存在惩罚: {presencePenalty[0]}</Label>
              <Slider
                value={presencePenalty}
                onValueChange={setPresencePenalty}
                max={2}
                min={0}
                step={0.1}
                className="w-full"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="isActive"
                checked={isActive}
                onCheckedChange={setIsActive}
              />
              <Label htmlFor="isActive">启用配置</Label>
            </div>

            <div className="flex justify-end space-x-2 pt-4">
              <Button variant="outline" onClick={onClose}>
                取消
              </Button>
              <Button 
                onClick={handleSave} 
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    保存中...
                  </>
                ) : (
                  "保存"
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}