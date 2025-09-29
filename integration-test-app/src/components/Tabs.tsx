import type { ReactNode } from 'react'

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
          background: '#ffffff',
          borderBottom: '1px solid #e5e7eb',
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
                border: isActive ? '1px solid #93c5fd' : '1px solid #e5e7eb',
                background: isActive ? '#eff6ff' : '#ffffff',
                color: isActive ? '#1d4ed8' : '#111827',
                fontWeight: isActive ? 600 : 500,
                cursor: 'pointer',
              }}
            >
              {it.label}
            </button>
          )
        })}
      </div>
      <div style={{ padding: 16 }}>
        {items.find((it) => it.key === activeKey)?.content}
      </div>
    </div>
  )
}


