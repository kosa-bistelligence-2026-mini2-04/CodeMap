import type { Result } from '../types/index.js'

export function ok<T>(data: T): Result<T> {
  return [null, data]
}

export function err<E extends Error>(error: E): Result<never, E> {
  return [error, null]
}

export function isErr<T, E extends Error>(result: Result<T, E>): result is [E, null] {
  return result[0] !== null
}

export function isOk<T, E extends Error>(result: Result<T, E>): result is [null, T] {
  return result[0] === null
}
