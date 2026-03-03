"use client";

import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabTrigger } from "@/components/ui/tabs";
import { WOECalculator } from "./woe-calculator";
import { IVAnalyzer } from "./iv-analyzer";
import { FeatureSelector } from "./feature-selector";
import { BarChart3, TrendingUp, Filter, Info } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function ScorecardContainer() {
  const [activeTab, setActiveTab] = useState("woe");

  return (
    <div className="w-full space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">评分卡分析工具</h1>
        <p className="text-muted-foreground mt-2">
          使用 WOE、IV 和特征选择进行金融风险评估
        </p>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <BarChart3 className="w-5 h-5" />
              WOE 计算
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              计算单个特征的权重证据，量化特征对目标变量的差异度
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="w-5 h-5" />
              信息价值
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              批量分析所有特征的预测力，自动排序关键特征
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Filter className="w-5 h-5" />
              特征选择
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              根据 IV 阈值自动选择高价值特征，简化模型
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>分析工具</CardTitle>
          <CardDescription>
            选择分析类型开始工作，支持 CSV 数据上传
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabTrigger value="woe" className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                <span className="hidden sm:inline">WOE 计算</span>
              </TabTrigger>
              <TabTrigger value="iv" className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                <span className="hidden sm:inline">IV 分析</span>
              </TabTrigger>
              <TabTrigger value="selection" className="flex items-center gap-2">
                <Filter className="w-4 h-4" />
                <span className="hidden sm:inline">特征选择</span>
              </TabTrigger>
            </TabsList>

            {/* WOE Tab */}
            <TabsContent value="woe" className="space-y-4">
              <WOECalculator />
            </TabsContent>

            {/* IV Tab */}
            <TabsContent value="iv" className="space-y-4">
              <IVAnalyzer />
            </TabsContent>

            {/* Feature Selection Tab */}
            <TabsContent value="selection" className="space-y-4">
              <FeatureSelector />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Help Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="w-5 h-5" />
            使用指南
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-semibold mb-2">1. WOE (权重证据) 计算</h4>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>选择一个特征和目标变量</li>
              <li>选择分箱方法（等频、等宽、K-means）</li>
              <li>
                系统自动计算每个分箱的 WOE 和 IV 值
              </li>
              <li>IV 值表示特征的预测力（0.1-0.3 为中等，&gt;0.3 为强）</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">2. IV (信息价值) 分析</h4>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>自动分析所有数值特征</li>
              <li>按 IV 值自动排序，显示特征重要性</li>
              <li>查看特征的预测力强度</li>
              <li>导出分析结果用于后续建模</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-2">3. 特征选择</h4>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>设置 IV 阈值（推荐 0.1）</li>
              <li>系统自动选择满足条件的特征</li>
              <li>降低模型复杂度，提升效率</li>
              <li>支持复制特征列表和下载结果</li>
            </ul>
          </div>

          <div className="bg-muted p-3 rounded-lg">
            <p className="font-semibold mb-2">💡 提示</p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>上传的 CSV 文件第一行应为列名</li>
              <li>目标变量应为二分类（0/1）</li>
              <li>数值特征会自动被分析</li>
              <li>建议样本量至少 100+ 行</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
