import { useCallback, useEffect, useState } from 'react'
import { Button, Divider, Input, Modal, Space, Tag } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { isValidCron } from 'cron-validator'
import cronstrue from 'cronstrue'
import { nlToCron } from '@/utils/nl-to-cron'

interface CronGeneratorProps {
  open: boolean
  onClose: () => void
  onApply: (cronExpression: string) => void
}

const PRESETS = [
  { label: 'Every hour', cron: '0 * * * *', nl: 'every hour' },
  { label: 'Daily at 9am', cron: '0 9 * * *', nl: 'daily at 9am' },
  { label: 'Weekdays at 6pm', cron: '0 18 * * 1-5', nl: 'weekdays at 6pm' },
  { label: 'Every Monday', cron: '0 0 * * 1', nl: 'every Monday' },
  { label: 'Every 30 min', cron: '*/30 * * * *', nl: 'every 30 minutes' },
]

export default function CronGenerator({ open, onClose, onApply }: CronGeneratorProps) {
  const [nlInput, setNlInput] = useState('')
  const [result, setResult] = useState<{ cron: string; description: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cronValid, setCronValid] = useState<boolean | null>(null)

  useEffect(() => {
    if (!open) {
      setNlInput('')
      setResult(null)
      setError(null)
      setCronValid(null)
    }
  }, [open])

  const handleGenerate = useCallback(() => {
    const trimmed = nlInput.trim()
    if (!trimmed) {
      setError('Please enter a description of your schedule')
      setResult(null)
      setCronValid(null)
      return
    }

    const parsed = nlToCron(trimmed)
    if (!parsed) {
      setError('Could not understand this description. Try one of the presets above.')
      setResult(null)
      setCronValid(null)
      return
    }

    setError(null)
    setCronValid(isValidCron(parsed.cron, { seconds: false }))

    try {
      const enriched = cronstrue.toString(parsed.cron)
      setResult({ ...parsed, description: enriched })
    } catch {
      setResult(parsed)
    }
  }, [nlInput])

  const handlePreset = useCallback((nl: string, cron: string) => {
    setNlInput(nl)
    setError(null)
    setCronValid(isValidCron(cron, { seconds: false }))
    try {
      const desc = cronstrue.toString(cron)
      setResult({ cron, description: desc })
    } catch {
      setResult({ cron, description: '' })
    }
  }, [])

  const handleApply = useCallback(() => {
    if (result && cronValid) {
      onApply(result.cron)
      onClose()
    }
  }, [result, cronValid, onApply, onClose])

  return (
    <Modal
      title="Cron Expression Generator"
      open={open}
      onCancel={onClose}
      width={500}
      footer={
        <Space>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="primary" disabled={!result || !cronValid} onClick={handleApply}>
            Apply
          </Button>
        </Space>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 8 }}>
        {/* Natural language input */}
        <div>
          <div style={{ marginBottom: 6, fontSize: 13, color: 'var(--color-muted)' }}>
            Describe your schedule (English / 中文)
          </div>
          <Input
            value={nlInput}
            onChange={(e) => setNlInput(e.target.value)}
            onPressEnter={handleGenerate}
            placeholder="e.g., every day at 9am, weekdays at 6pm, 每天早上9点, 工作日18点"
            suffix={
              <Button
                type="text"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={handleGenerate}
                style={{ marginRight: -4 }}
              >
                Generate
              </Button>
            }
          />
        </div>

        {/* Presets */}
        <div>
          <div style={{ marginBottom: 6, fontSize: 13, color: 'var(--color-muted)' }}>
            Quick presets
          </div>
          <Space wrap>
            {PRESETS.map((p) => (
              <Button
                key={p.cron}
                size="small"
                onClick={() => handlePreset(p.nl, p.cron)}
                style={{ fontSize: 13 }}
              >
                {p.label}
              </Button>
            ))}
          </Space>
        </div>

        {/* Result */}
        {result && (
          <>
            <Divider style={{ margin: '4px 0' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontSize: 13, color: 'var(--color-muted)' }}>Generated Expression</div>
              <div
                style={{
                  padding: '10px 14px',
                  border: '1px solid var(--color-hairline)',
                  borderRadius: 'var(--radius-md)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 16,
                  background: 'var(--color-canvas)',
                  letterSpacing: '0.05em',
                }}
              >
                {result.cron}
              </div>
              <div style={{ fontSize: 14, color: 'var(--color-ink)' }}>
                {result.description}
              </div>
              <div>
                {cronValid ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    Valid cron expression
                  </Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    Invalid cron expression
                  </Tag>
                )}
              </div>
            </div>
          </>
        )}

        {/* Error */}
        {error && (
          <Tag color="error" style={{ padding: '4px 8px', whiteSpace: 'normal', height: 'auto' }}>
            {error}
          </Tag>
        )}
      </div>
    </Modal>
  )
}
