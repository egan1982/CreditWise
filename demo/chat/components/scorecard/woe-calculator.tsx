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
import { Spinner, Upload, Download, BarChart3, AlertCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface WOEResult {
  feature: string;
  iv: number;
  interpretation: string;
  strength: string;
  predictive: boolean;
  n_bins: number;
  woe: number[];
  bins: Array<{
    bin: string;
    event_count: number;
    non_event_count: number;
    event_rate: number;
    woe: number;
    iv_contribution: number;
  }>;
}

interface SampleRow {
  [key: string]: string | number;
}

export function WOECalculator() {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [data, setData] = useState<SampleRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WOEResult | null>(null);

  const [formData, setFormData] = useState({
    feature: "",
    target: "",
    n_bins: 5,
    method: "quantile" as "quantile" | "uniform" | "kmeans",
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
      setFormData({ ...formData, feature: "", target: "" });
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

  // Calculate WOE
  const handleCalculate = async () => {
    if (!formData.feature || !formData.target || data.length === 0) {
      toast({
        title: "错误",
        description: "请选择特征、目标变量并上传数据",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("http://localhost:8200/v1/scorecard/woe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data,
          feature: formData.feature,
          target: formData.target,
          n_bins: formData.n_bins,
          method: formData.method,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result = await response.json();
      if (result.status === "success") {
        setResult(result.data);
        toast({
          title: "成功",
          description: `WOE 计算完成，IV = ${result.data.iv.toFixed(4)}`,
        });
      } else {
        throw new Error(result.error || "计算失败");
      }
    } catch (error) {
      toast({
        title: "错误",
        description: error instanceof Error ? error.message : "计算失败",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
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
      a.download = `woe_${formData.feature}_${Date.now()}.json`;
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
          report_type: 'woe',
          format: format === 'pdf' ? 'html' : format,
          title: `WOE 分析报告 - ${result.feature}`,
          data: result
        })
      });
      const data = await response.json();
      
      if (data.success && data.content) {
        if (format === 'pdf') {
          // 打开新窗口显示HTML，用户可通过浏览器打印为PDF
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
          a.download = data.filename || `woe_report_${Date.now()}.xlsx`;
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
          a.download = data.filename || `woe_report_${Date.now()}.docx`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast({
            title: "下载成功",
            description: "Word报告已下载",
          });
        } else {
          // HTML格式直接下载
          const blob = new Blob([data.content], { type: "text/html;charset=utf-8" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = data.filename || `woe_report_${Date.now()}.html`;
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
            <BarChart3 className="w-5 h-5" />
            WOE 计算工具
          </CardTitle>
          <CardDescription>
            计算特征的 Weight of Evidence 和信息价值
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

          {/* Column Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">特征列</label>
              <Select
                value={formData.feature}
                onValueChange={(v) =>
                  setFormData({ ...formData, feature: v })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择特征" />
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

            <div className="space-y-2">
              <label className="text-sm font-medium">目标列</label>
              <Select
                value={formData.target}
                onValueChange={(v) =>
                  setFormData({ ...formData, target: v })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择目标" />
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
          </div>

          {/* Parameters */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">分箱方法</label>
              <Select
                value={formData.method}
                onValueChange={(v: any) =>
                  setFormData({ ...formData, method: v })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="quantile">等频分箱 (Quantile)</SelectItem>
                  <SelectItem value="uniform">等宽分箱 (Uniform)</SelectItem>
                  <SelectItem value="kmeans">K-means 分箱</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                分箱数: {formData.n_bins}
              </label>
              <Slider
                value={[formData.n_bins]}
                onValueChange={(v) =>
                  setFormData({ ...formData, n_bins: v[0] })
                }
                min={2}
                max={20}
                step={1}
              />
            </div>
          </div>

          {/* Button */}
          <Button
            onClick={handleCalculate}
            disabled={loading || data.length === 0}
            className="w-full"
          >
            {loading ? (
              <>
                <Spinner className="w-4 h-4 mr-2 animate-spin" />
                计算中...
              </>
            ) : (
              "开始计算 WOE"
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>计算结果</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-4 gap-4">
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">特征</p>
                <p className="text-lg font-bold">{result.feature}</p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">IV 值</p>
                <p className="text-lg font-bold">{result.iv.toFixed(4)}</p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">强度</p>
                <p className="text-lg font-bold">{result.strength}</p>
              </div>
              <div className="p-3 border rounded-lg">
                <p className="text-sm text-muted-foreground">预测力</p>
                <p className="text-lg font-bold">
                  {result.predictive ? "有" : "无"}
                </p>
              </div>
            </div>

            {/* Interpretation */}
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{result.interpretation}</AlertDescription>
            </Alert>

            {/* Bins Table */}
            <div>
              <h3 className="font-semibold mb-3">分箱详情</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">分箱</th>
                      <th className="text-right p-2">事件数</th>
                      <th className="text-right p-2">非事件数</th>
                      <th className="text-right p-2">事件率</th>
                      <th className="text-right p-2">WOE</th>
                      <th className="text-right p-2">IV 贡献</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.bins.map((bin, i) => (
                      <tr key={i} className="border-b">
                        <td className="p-2">{bin.bin}</td>
                        <td className="text-right p-2">{bin.event_count}</td>
                        <td className="text-right p-2">
                          {bin.non_event_count}
                        </td>
                        <td className="text-right p-2">
                          {(bin.event_rate * 100).toFixed(1)}%
                        </td>
                        <td className="text-right p-2">
                          {bin.woe.toFixed(4)}
                        </td>
                        <td className="text-right p-2">
                          {bin.iv_contribution.toFixed(6)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

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
          </CardContent>
        </Card>
      )}
    </div>
  );
}
