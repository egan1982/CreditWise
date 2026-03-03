"use client"

import * as React from "react"
import { Check, ChevronsUpDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

export interface ComboboxOption {
  value: string
  label: string
}

export interface ComboboxProps {
  /** 选项列表 */
  options: ComboboxOption[]
  /** 当前值 */
  value?: string
  /** 值变化回调 */
  onValueChange?: (value: string) => void
  /** 占位符 */
  placeholder?: string
  /** 搜索框占位符 */
  searchPlaceholder?: string
  /** 无结果提示 */
  emptyText?: string
  /** 是否允许自定义输入（不在选项中的值） */
  allowCustom?: boolean
  /** 自定义输入提示 */
  customInputHint?: string
  /** 是否禁用 */
  disabled?: boolean
  /** 自定义类名 */
  className?: string
  /** 触发器类名 */
  triggerClassName?: string
}

export function Combobox({
  options,
  value,
  onValueChange,
  placeholder = "请选择...",
  searchPlaceholder = "搜索或输入...",
  emptyText = "无匹配项",
  allowCustom = true,
  customInputHint = "按回车使用输入值",
  disabled = false,
  className,
  triggerClassName,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const [inputValue, setInputValue] = React.useState("")

  // 获取显示文本
  const displayValue = React.useMemo(() => {
    if (!value) return ""
    const option = options.find((opt) => opt.value === value)
    return option ? option.label : value
  }, [value, options])

  // 处理选择
  const handleSelect = React.useCallback(
    (selectedValue: string) => {
      onValueChange?.(selectedValue === value ? "" : selectedValue)
      setOpen(false)
      setInputValue("")
    },
    [value, onValueChange]
  )

  // 处理自定义输入
  const handleCustomInput = React.useCallback(() => {
    if (allowCustom && inputValue.trim()) {
      onValueChange?.(inputValue.trim())
      setOpen(false)
      setInputValue("")
    }
  }, [allowCustom, inputValue, onValueChange])

  // 处理键盘事件
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && allowCustom && inputValue.trim()) {
        // 检查是否有匹配的选项
        const matchedOption = options.find(
          (opt) =>
            opt.label.toLowerCase() === inputValue.toLowerCase() ||
            opt.value.toLowerCase() === inputValue.toLowerCase()
        )
        if (!matchedOption) {
          e.preventDefault()
          handleCustomInput()
        }
      }
    },
    [allowCustom, inputValue, options, handleCustomInput]
  )

  // 过滤后的选项
  const filteredOptions = React.useMemo(() => {
    if (!inputValue) return options
    const search = inputValue.toLowerCase()
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(search) ||
        opt.value.toLowerCase().includes(search)
    )
  }, [options, inputValue])

  // 是否显示自定义输入提示
  const showCustomHint = React.useMemo(() => {
    if (!allowCustom || !inputValue.trim()) return false
    // 如果输入值不在选项中，显示提示
    const exactMatch = options.some(
      (opt) =>
        opt.label.toLowerCase() === inputValue.toLowerCase() ||
        opt.value.toLowerCase() === inputValue.toLowerCase()
    )
    return !exactMatch
  }, [allowCustom, inputValue, options])

  return (
    <div className={cn("w-full", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "w-full justify-between font-normal",
              !value && "text-muted-foreground",
              triggerClassName
            )}
          >
            <span className="truncate">
              {displayValue || placeholder}
            </span>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder={searchPlaceholder}
              value={inputValue}
              onValueChange={setInputValue}
              onKeyDown={handleKeyDown}
            />
            <CommandList>
              {filteredOptions.length === 0 && !showCustomHint && (
                <CommandEmpty>{emptyText}</CommandEmpty>
              )}
              {showCustomHint && (
                <CommandItem
                  value={inputValue}
                  onSelect={handleCustomInput}
                  className="text-blue-600 dark:text-blue-400"
                >
                  <span className="flex-1 truncate">
                    使用 &quot;{inputValue}&quot;
                  </span>
                  <span className="text-xs text-muted-foreground ml-2">
                    {customInputHint}
                  </span>
                </CommandItem>
              )}
              <CommandGroup>
                {filteredOptions.map((option) => (
                  <CommandItem
                    key={option.value}
                    value={option.value}
                    onSelect={() => handleSelect(option.value)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === option.value ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <span className="truncate">{option.label}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  )
}

export default Combobox
