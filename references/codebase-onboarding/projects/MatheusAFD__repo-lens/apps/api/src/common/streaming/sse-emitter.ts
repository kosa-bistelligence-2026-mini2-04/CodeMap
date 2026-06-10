export function toMessageEvent<T>(event: T): MessageEvent {
  return new MessageEvent('message', { data: JSON.stringify(event) })
}
