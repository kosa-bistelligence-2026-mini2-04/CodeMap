import { Subject } from 'rxjs'

export class SseSubjectPool<TEvent> {
  private readonly subjects = new Map<string, Subject<MessageEvent>>()

  create(key: string): Subject<MessageEvent> {
    const subject = new Subject<MessageEvent>()
    this.subjects.set(key, subject)
    return subject
  }

  set(key: string, subject: Subject<MessageEvent>): void {
    this.subjects.set(key, subject)
  }

  get(key: string): Subject<MessageEvent> | undefined {
    return this.subjects.get(key)
  }

  has(key: string): boolean {
    return this.subjects.has(key)
  }

  emit(key: string, event: TEvent): void {
    const subject = this.subjects.get(key)
    if (!subject) return
    subject.next(new MessageEvent('message', { data: JSON.stringify(event) }))
  }

  complete(key: string): void {
    const subject = this.subjects.get(key)
    if (!subject) return
    subject.complete()
    this.subjects.delete(key)
  }

  delete(key: string): void {
    this.subjects.delete(key)
  }
}
