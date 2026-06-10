type LogData = Record<string, unknown>

function formatLog(data: LogData, message: string): string {
  const parts = Object.entries(data)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(' ')
  return `${message} ${parts}`
}

export const logger = {
  info(data: LogData, message: string) {
    console.info(formatLog(data, message))
  },
  error(data: LogData, message: string) {
    console.error(formatLog(data, message))
  },
  warn(data: LogData, message: string) {
    console.warn(formatLog(data, message))
  },
}
