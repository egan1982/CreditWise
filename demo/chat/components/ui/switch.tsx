'use client'

import * as React from 'react'
import * as SwitchPrimitive from '@radix-ui/react-switch'

import { cn } from '@/lib/utils'

function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      className={cn(
        'peer inline-flex h-[1.15rem] w-8 shrink-0 items-center rounded-full border shadow-xs transition-all outline-none disabled:cursor-not-allowed disabled:opacity-50',
        // 选中状态：主色背景
        'data-[state=checked]:bg-primary data-[state=checked]:border-primary',
        // 未选中状态：灰色背景，更明显的边框
        'data-[state=unchecked]:bg-gray-200 data-[state=unchecked]:border-gray-300',
        'dark:data-[state=unchecked]:bg-gray-600 dark:data-[state=unchecked]:border-gray-500',
        // 焦点状态
        'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]',
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className={cn(
          'pointer-events-none block size-4 rounded-full ring-0 transition-transform',
          'data-[state=checked]:translate-x-[calc(100%-2px)] data-[state=unchecked]:translate-x-0',
          // 滑块颜色
          'bg-white dark:data-[state=unchecked]:bg-gray-200 dark:data-[state=checked]:bg-white',
        )}
      />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
