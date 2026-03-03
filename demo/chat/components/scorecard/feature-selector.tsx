"use client";

import React, { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Spinner,
  Upload,
  Download,
  Filter,
  AlertCircle,
  Copy,
  Check,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface SelectionResult {
  target: string;
  iv_threshold: number;
  total_features: number;
  selected_count: number;
  selected_features: string[];
  selection_details: Array<{
    feature: string;
    iv: number;
    strength: string;
  }>;
}

interface SampleRow {
  [key: string]: string | number;
}

export function FeatureSelector() {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [data, setData] = useState<SampleRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SelectionResult | null>(null);
  const [copied, setCopied] = useState(false);

  const [formData, setFormData] = useState({
    target: "",
    iv_threshold: 0.1,
  });

  // Parse CSV file
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const lines = text.trim().split("\n");
      const headers = lines[0].split(",").map((h) => h.trim());

      const rows: SampleRow[] = lines.slice(1).map((line) => {
        const values = line.split(",").map((v) => v.trim());
        const row: SampleRow = {};
        headers.forEach((header, index) => {
          const val = values[index];
          row[header] = isNaN(Number(val)) ? val : Number(val);
        });
        return row;
      });

      setData(rows);
      setColumns(headers);
      setFormData({ ...formData, target: "" });
      toast({
        title: "成功",
        description: `已加载 ${rows.length} 行数据，${headers.length} 列`,
      });
    } catch (error) {
      toast({
        title: "错误",
        description: "无法解析 CSV 文件",
        variant: "destructive",
      });
    }
  };

  // Select features
  const handleSelect = async () => {
    if (!formData.target || data.length === 0) {
      toast({
        title: "错误",
        description: "请选择目标变量并上传数据",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8200/v1/scorecard/feature-selection",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            data,
            target: formData.target,
            iv_threshold: formData.iv_threshold,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result = await response.json();
      if (result.status === "success") {
        setResult(result.data);
        toast({
          title: "成功",
          description: `特征选择完成，选中 ${result.data.selected_count} 个特征`,
        });
      } else {
        throw new Error(result.error || "特征选择失败");
      }
    } catch (error) {
      toast({
        title: "错误",
        description: error instanceof Error ? error.message : "特征选择失败",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // Copy to clipboard
  const handleCopyFeatures = () => {
    if (!result) return;
    const text = result.selected_features.join(", ");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast({
      title: "已复制",
      description: "特征列表已复制到剪贴板",
    });
  };

  // Download results - 支持多种格式
  const handleDownload = async (format: 'json' | 'html' | 'excel' | 'word' | 'pdf' = 'json') => {
    if (!result) return;
    
    if (format === 'json') {
      // JSON 格式直接下载
      const text = JSON.stringify(result, null, 2);
      const blob = new Blob([text], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `feature_selection_${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast({
        title: "下载成功",
        description: "JSON结果已下载",
      });
      return;
    }
    
    // 调用后端API生成报告
    try {
      const response = await fetch("http://localhost:8200/v1/export/generic-report", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report_type: 'feature_selection',
          format: format === 'pdf' ? 'html' : format,
          title: '特征选择报告',
          data: result
        })
      });
      const data = await response.json();
      
      if (data.success && data.content) {
        if (format === 'pdf') {
          const printWindow = window.open('', '_blank');
          if (printWindow) {
            printWindow.document.write(data.content);
            printWindow.document.close();
            setTimeout(() => {
              printWindow.print();
            }, 500);
            toast({
              title: "PDF导出",
              description: '请在打印对话框中选择"另存为PDF"',
            });
          } else {
            toast({
              title: "导出失败",
              description: "无法打开新窗口，请检查浏览器弹窗设置",
              variant: "destructive",
            });
          }
        } else if (format === 'excel') {
          const binaryString = atob(data.content);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = data.filename || `feature_selection_report_${Date.now()}.xlsx`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast({
            title: "下载成功",
            description: "Excel报告已下载",
          });
        } else if (format === 'word') {
          const binaryString = atob(data.content);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = data.filename || `feature_selection_report_${Date.now()}.docx`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast({
            title: "下载成功",
            description: "Word报告已下载",
          });
        } else {
          const blob = new Blob([data.content], { type: "text/html;charset=utf-8" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = data.filename || `feature_selection_report_${Date.now()}.html`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast({
            title: "下载成功",
            description: "HTML报告已下载",
          });
        }
      } else {
        toast({
          title: "下载失败",
          description: data.error || "生成报告失败",
          variant: "destructive",
        });
      }
    } catch (err) {
      toast({
        title: "下载失败",
        description: "网络错误，请重试",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            特征选择工具
          </CardTitle>
          <CardDescription>
            基于信息价值 (IV) 阈值自动选择重要特征
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* File Upload */}
          <div className="space-y-2">
            <label className="text-sm font-medium">上传数据 (CSV)</label>
            <div className="flex gap-2">
              <Input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                ref={fileInputRef}
                className="cursor-pointer"
              />
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="w-4 h-4 mr-2" />
                浏览
              </Button>
            </div>
            {data.length > 0 && (
              <p className="text-xs text-muted-foreground">
                已加载: {data.length} 行 × {columns.length} 列
              </p>
            )}
          </div>

          {/* Target Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">目标列</label>
            <Select
              value={formData.target}
              onValueChange={(v) =>
                setFormData({ ...formData, target: v })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="选择目标变量" />
              </SelectTrigger>
              <SelectContent>
                {columns.map((col) => (
                  <SelectItem key={col} value={col}>
                    {col}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* IV Threshold */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              IV 阈值: {formData.iv_threshold.toFixed(3)}
            </label>
            <Slider
              value={[formData.iv_threshold * 1000]}
              onValueChange={(v) =>
                setFormData({ ...formData, iv_threshold: v[0] / 1000 })
              }
              min={0}
              max={500}
              step={10}
            />
            <p className="text-xs text-muted-foreground">
              选择 IV 值大于等于此阈值的特征
            </p>
          </div>

          {/* Select Button */}
          <Button
            onClick={handleSelect}
            disabled={loading || data.length === 0}
            className="w-full"
          >
            {loading ? (
              <>
                <Spinner className="w-4 h-4 mr-2 animate-spin" />
                处理中...
              </>
            ) : (
              "开始特征选择"
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <>
          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle>选择结果</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">总特征</p>
                  <p className="text-2xl font-bold">
                    {result.total_features}
                  </p>
                </div>
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">选中特征</p>
                  <p className="text-2xl font-bold">
                    {result.selected_count}
                  </p>
                </div>
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">IV 阈值</p>
                  <p className="text-2xl font-bold">
                    {result.iv_threshold.toFixed(3)}
                  </p>
                </div>
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">选中率</p>
                  <p className="text-2xl font-bold">
                    {(
                      (result.selected_count / result.total_features) *
                      100
                    ).toFixed(1)}
                    %
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Selected Features */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>已选择的特征</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCopyFeatures}
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 mr-2" />
                      已复制
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2" />
                      复制
                    </>
                  )}
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {result.selected_features.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {result.selected_features.map((feature) => (
                      <div
                        key={feature}
                        className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm"
                      >
                        {feature}
                      </div>
                    ))}
                  </div>
                ) : (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      没有特征满足 IV 阈值条件，请尝试降低阈值
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Details Table */}
          <Card>
            <CardHeader>
              <CardTitle>特征详情</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">特征</th>
                      <th className="text-right p-2">IV 值</th>
                      <th className="text-left p-2">强度</th>
                      <th className="text-center p-2">已选中</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.selection_details.map((item) => (
                      <tr key={item.feature} className="border-b">
                        <td className="p-2 font-medium">{item.feature}</td>
                        <td className="text-right p-2 font-bold">
                          {item.iv.toFixed(4)}
                        </td>
                        <td className="p-2">{item.strength}</td>
                        <td className="text-center p-2">
                          {item.iv >= result.iv_threshold ? (
                            <Check className="w-4 h-4 text-green-600 mx-auto" />
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Download Buttons */}
          <div className="flex flex-wrap gap-2">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={() => handleDownload('html')} variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-1" />
                    HTML
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载HTML报告</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={() => handleDownload('excel')} variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-1" />
                    Excel
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Excel报告</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={() => handleDownload('word')} variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-1" />
                    Word
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载Word报告</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={() => handleDownload('pdf')} variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-1" />
                    PDF
                  </Button>
                </TooltipTrigger>
                <TooltipContent>打印为PDF</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button onClick={() => handleDownload('json')} variant="outline" size="sm">
                    <Download className="w-4 h-4 mr-1" />
                    JSON
                  </Button>
                </TooltipTrigger>
                <TooltipContent>下载JSON数据</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </>
      )}
    </div>
  );
}
