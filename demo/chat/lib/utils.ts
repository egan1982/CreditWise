import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 解包后端通过 safe_serialize 序列化后的数据
 * 
 * 后端 sop_api.py 的 safe_serialize 函数会将 DataFrame、dict、list 等类型
 * 序列化为 { type: "dataframe" | "dict" | "list" | ..., data: 实际数据 } 格式
 * 
 * 此函数用于提取实际数据，如果输入不是包装格式则直接返回原值
 * 
 * @param raw - 可能被包装的原始数据
 * @returns 解包后的实际数据
 * 
 * @example
 * // DataFrame 格式
 * unwrapData({ type: "dataframe", data: [{...}, {...}] }) // => [{...}, {...}]
 * 
 * // dict 格式
 * unwrapData({ type: "dict", data: { key: "value" } }) // => { key: "value" }
 * 
 * // 未包装的原始数据
 * unwrapData([1, 2, 3]) // => [1, 2, 3]
 * unwrapData(null) // => null
 */
export function unwrapData<T = unknown>(raw: unknown): T {
  if (raw && typeof raw === 'object' && 'data' in raw) {
    return (raw as { data: T }).data;
  }
  return raw as T;
}
