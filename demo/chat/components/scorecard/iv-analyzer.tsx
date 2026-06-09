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
import { Badge } from "@/components/ui/badge";
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
  TrendingUp,
  AlertCircle,
  Check,
  X,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from "recharts";

interface IVResult {
  feature: string;
  iv: number;
  strength: string;
  interpretation: string;
  predictive: boolean;
  rank?: number;
  n_bins: number;
}

interface AnalysisResult {
  target: string;
  total_features: number;
  analyzed_features: number;
  results: IVResult[];
  summary: {
    avg_iv: number;
    max_iv: number;
    strong_predictors: number;
    medium_predictors: number;
    weak_predictors: number;
  };
}

interface SampleRow {
  [key: string]: string | number;
}

export function IVAnalyzer() {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [data, setData] = useState<SampleRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const [formData, setFormData] = useState({
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

  // Analyze IV
  const handleAnalyze = async () => {
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
      const response = await fetch("http://localhost:8200/v1/scorecard/iv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data,
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
          description: `分析完成，已分析 ${result.data.analyzed_features} 个特征`,
        });
      } else {
        throw new Error(result.error || "分析失败");
      }
    } catch (error) {
      toast({
        title: "错误",
        description: error instanceof Error ? error.message : "分析失败",
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
      a.download = `iv_analysis_${Date.now()}.json`;
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
          report_type: 'iv',
          format: format === 'pdf' ? 'html' : format,
          title: 'IV 分析报告',
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
          a.download = data.filename || `iv_report_${Date.now()}.xlsx`;
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
          a.download = data.filename || `iv_report_${Date.now()}.docx`;
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
          a.download = data.filename || `iv_report_${Date.now()}.html`;
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

  const chartData = result?.results
    .filter((r) => r.rank)
    .slice(0, 10)
    .map((r) => ({
      feature: r.feature.substring(0, 15),
      iv: parseFloat(r.iv.toFixed(4)),
    })) || [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            信息价值 (IV) 分析
          </CardTitle>
          <CardDescription>批量分析特征的信息价值和预测力</CardDescription>
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

          {/* Analysis Method */}
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

          {/* Analyze Button */}
          <Button
            onClick={handleAnalyze}
            disabled={loading || data.length === 0}
            className="w-full"
          >
            {loading ? (
              <>
                <Spinner className="w-4 h-4 mr-2 animate-spin" />
                分析中...
              </>
            ) : (
              "开始分析"
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
              <CardTitle>分析摘要</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-5 gap-4">
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">总特征数</p>
                  <p className="text-2xl font-bold">{result.total_features}</p>
                </div>
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">已分析</p>
                  <p className="text-2xl font-bold">
                    {result.analyzed_features}
                  </p>
                </div>
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">平均 IV</p>
                  <p className="text-2xl font-bold">
                    {result.summary.avg_iv.toFixed(4)}
                  </p>
                </div>
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">强预测 (&gt;0.3)</p>
                  <p className="text-2xl font-bold text-green-600">
                    {result.summary.strong_predictors}
                  </p>
                </div>
                <div className="p-3 border rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    弱预测 (&lt;0.1)
                  </p>
                  <p className="text-2xl font-bold text-red-600">
                    {result.summary.weak_predictors}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Chart */}
          {chartData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Top 10 特征 IV 值</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="feature" />
                    <YAxis />
                    <RechartsTooltip />
                    <Bar dataKey="iv" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Results Table */}
          <Card>
            <CardHeader>
              <CardTitle>详细结果</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">排名</th>
                      <th className="text-left p-2">特征</th>
                      <th className="text-right p-2">IV 值</th>
                      <th className="text-left p-2">强度</th>
                      <th className="text-center p-2">预测力</th>
                      <th className="text-left p-2">解释</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.results
                      .filter((r) => r.rank)
                      .map((item) => (
                        <tr key={item.feature} className="border-b">
                          <td className="p-2">#{item.rank}</td>
                          <td className="p-2 font-medium">{item.feature}</td>
                          <td className="text-right p-2 font-bold">
                            {item.iv.toFixed(4)}
                          </td>
                          <td className="p-2">
                            <Badge
                              variant={
                                item.strength === "强" ||
                                item.strength === "极强"
                                  ? "default"
                                  : item.strength === "中"
                                  ? "secondary"
                                  : "outline"
                              }
                            >
                              {item.strength}
                            </Badge>
                          </td>
                          <td className="text-center p-2">
                            {item.predictive ? (
                              <Check className="w-4 h-4 text-green-600 mx-auto" />
                            ) : (
                              <X className="w-4 h-4 text-red-600 mx-auto" />
                            )}
                          </td>
                          <td className="p-2 text-muted-foreground text-xs">
                            {item.interpretation}
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
