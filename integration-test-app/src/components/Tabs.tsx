import type { ReactNode } from 'react'
import { colors } from '../theme'

export type TabItem = {
  key: string
  label: string
  content: ReactNode
}

type TabsProps = {
  items: TabItem[]
  activeKey: string
  onChange: (key: string) => void
}

export default function Tabs({ items, activeKey, onChange }: TabsProps) {
  return (
    <div>
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 1000,
          display: 'flex',
          gap: 8,
          padding: '8px 16px',
          background: colors.background,
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        {items.map((it) => {
          const isActive = activeKey === it.key
          return (
            <button
              key={it.key}
              onClick={() => onChange(it.key)}
              style={{
                padding: '8px 12px',
                borderRadius: 6,
                border: isActive ? `1px solid ${colors.primarySoftBorder}` : `1px solid ${colors.border}`,
                background: isActive ? colors.primarySoftBg : colors.surface,
                color: isActive ? colors.primary : colors.textPrimary,
                fontWeight: isActive ? 600 : 500,
                cursor: 'pointer',
              }}
            >
              {it.label}
            </button>
          )
        })}
      </div>
      <div style={{ padding: 16, color: colors.textPrimary }}>
        {items.find((it) => it.key === activeKey)?.content}
      </div>
    </div>
  )
}


