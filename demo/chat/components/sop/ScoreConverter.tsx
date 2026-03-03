"use client";

import React, { useState, useCallback } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { ArrowLeftRight, Calculator, Loader2, Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { getApiUrl } from "@/lib/config";

// TypeScript interfaces
interface ScoreScale {
  base_score: number;
  pdo: number;
  rate?: number;
  bad_rate: number;
  base_odds: number;
  A: number;
  B: number;
  down_lmt?: number;
  up_lmt?: number;
}

interface ConvertResult {
  input: number;
  output: number;
}

interface ScoreConverterProps {
  scaleInfo: ScoreScale | null;
  className?: string;
}

export function ScoreConverter({ scaleInfo, className }: ScoreConverterProps) {
  const [singleValue, setSingleValue] = useState<string>("");
  const [singleResult, setSingleResult] = useState<number | null>(null);
  const [batchValues, setBatchValues] = useState<string>("");
  const [batchResults, setBatchResults] = useState<ConvertResult[]>([]);
  const [direction, setDirection] = useState<"to_prob" | "to_score">("to_prob");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Convert single value locally (for quick feedback)
  const convertLocally = useCallback((value: number, dir: "to_prob" | "to_score"): number => {
    if (!scaleInfo) return 0;
    
    const { A, B } = scaleInfo;
    
    if (dir === "to_prob") {
      // Score → Probability
      // p = 1 / (1 + exp((A - Score) / B))
      return 1 / (1 + Math.exp((A - value) / B));
    } else {
      // Probability → Score
      // Score = A - B * log(p / (1-p))
      const clampedProb = Math.max(0.0001, Math.min(0.9999, value));
      const odds = clampedProb / (1 - clampedProb);
      return A - B * Math.log(odds);
    }
  }, [scaleInfo]);

  // Handle single conversion
  const handleSingleConvert = useCallback(() => {
    const value = parseFloat(singleValue);
    if (isNaN(value)) {
      setError("请输入有效数字");
      return;
    }
    
    setError(null);
    const result = convertLocally(value, direction);
    setSingleResult(result);
  }, [singleValue, direction, convertLocally]);

  // Handle batch conversion via API
  const handleBatchConvert = useCallback(async () => {
    const values = batchValues
      .split(/[,，\s\n]+/)
      .map(v => parseFloat(v.trim()))
      .filter(v => !isNaN(v));
    
    if (values.length === 0) {
      setError("请输入有效数字（逗号或换行分隔）");
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(getApiUrl("/sop/score/convert"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          values,
          direction,
          scale_params: scaleInfo ? {
            base_score: scaleInfo.base_score,
            pdo: scaleInfo.pdo,
            bad_rate: scaleInfo.bad_rate,
          } : undefined,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setBatchResults(data.results);
      } else {
        setError(data.error || "转换失败");
      }
    } catch (err) {
      // Fallback to local conversion
      const results = values.map(v => ({
        input: v,
        output: convertLocally(v, direction),
      }));
      setBatchResults(results);
    } finally {
      setIsLoading(false);
    }
  }, [batchValues, direction, scaleInfo, convertLocally]);

  // Format output value
  const formatOutput = (value: number, dir: "to_prob" | "to_score"): string => {
    if (dir === "to_prob") {
      return `${(value * 100).toFixed(2)}%`;
    } else {
      return Math.round(value).toString();
    }
  };

  if (!scaleInfo) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">
            评分刻度信息不可用
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Calculator className="h-4 w-4" />
          评分转换器
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p>基于评分刻度参数进行评分与概率的双向转换</p>
                <p className="mt-1 text-xs">公式: Score = A - B × log(odds)</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scale Parameters Display */}
        <div className="flex flex-wrap gap-2 p-3 bg-muted/50 rounded-lg text-sm">
          <Badge variant="outline">基准分: {scaleInfo.base_score}</Badge>
          <Badge variant="outline">PDO: {scaleInfo.pdo}</Badge>
          <Badge variant="outline">A: {scaleInfo.A.toFixed(2)}</Badge>
          <Badge variant="outline">B: {scaleInfo.B.toFixed(2)}</Badge>
          <Badge variant="outline">基础坏账率: {(scaleInfo.bad_rate * 100).toFixed(2)}%</Badge>
        </div>

        {/* Direction Toggle */}
        <div className="flex items-center gap-2">
          <Label>转换方向:</Label>
          <Button
            variant={direction === "to_prob" ? "default" : "outline"}
            size="sm"
            onClick={() => setDirection("to_prob")}
          >
            评分 → 概率
          </Button>
          <ArrowLeftRight className="h-4 w-4 text-muted-foreground" />
          <Button
            variant={direction === "to_score" ? "default" : "outline"}
            size="sm"
            onClick={() => setDirection("to_score")}
          >
            概率 → 评分
          </Button>
        </div>

        <Tabs defaultValue="single" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="single">单个转换</TabsTrigger>
            <TabsTrigger value="batch">批量转换</TabsTrigger>
          </TabsList>

          <TabsContent value="single" className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <Label className="text-xs text-muted-foreground">
                  {direction === "to_prob" ? "输入评分" : "输入概率 (0-1)"}
                </Label>
                <Input
                  type="number"
                  placeholder={direction === "to_prob" ? "例如: 680" : "例如: 0.15"}
                  value={singleValue}
                  onChange={(e) => setSingleValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSingleConvert()}
                />
              </div>
              <Button onClick={handleSingleConvert} className="mt-5">
                转换
              </Button>
              <div className="flex-1">
                <Label className="text-xs text-muted-foreground">
                  {direction === "to_prob" ? "对应概率" : "对应评分"}
                </Label>
                <div className="h-10 px-3 py-2 border rounded-md bg-muted/30 font-mono text-lg">
                  {singleResult !== null ? formatOutput(singleResult, direction) : "-"}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="batch" className="space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">
                输入多个值（逗号或换行分隔）
              </Label>
              <textarea
                className="w-full h-20 px-3 py-2 border rounded-md resize-none text-sm font-mono"
                placeholder={direction === "to_prob" 
                  ? "600, 650, 700, 750, 800" 
                  : "0.05, 0.10, 0.15, 0.20, 0.30"}
                value={batchValues}
                onChange={(e) => setBatchValues(e.target.value)}
              />
            </div>
            <Button onClick={handleBatchConvert} disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              批量转换
            </Button>

            {batchResults.length > 0 && (
              <div className="rounded-md border max-h-48 overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{direction === "to_prob" ? "评分" : "概率"}</TableHead>
                      <TableHead className="text-right">
                        {direction === "to_prob" ? "概率" : "评分"}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {batchResults.map((result, index) => (
                      <TableRow key={index}>
                        <TableCell className="font-mono">
                          {direction === "to_prob" 
                            ? result.input 
                            : `${(result.input * 100).toFixed(2)}%`}
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">
                          {formatOutput(result.output, direction)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default ScoreConverter;
