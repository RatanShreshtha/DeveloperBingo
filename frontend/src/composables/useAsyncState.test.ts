import { describe, expect, it } from 'vitest'
import { useAsyncState } from './useAsyncState'

describe('async state', () => {
  it('tracks pending, successful data, and an exposed failure', async () => {
    const state = useAsyncState<string>()
    let resolve!: (value: string) => void
    const operation = new Promise<string>((done) => {
      resolve = done
    })

    const running = state.run(() => operation)
    expect(state.pending.value).toBe(true)
    resolve('first')
    await running
    expect(state.data.value).toBe('first')
    expect(state.pending.value).toBe(false)

    const failure = new Error('offline')
    await state.run(() => Promise.reject(failure))
    expect(state.error.value).toBe(failure)
    expect(state.data.value).toBe('first')
    expect(state.pending.value).toBe(false)

    await state.run(() => Promise.resolve('second'))
    expect(state.data.value).toBe('second')
    expect(state.error.value).toBeNull()
  })

  it('does not let an older request overwrite a newer result', async () => {
    const state = useAsyncState<string>()
    let rejectOld!: (reason: Error) => void
    const old = state.run(
      () =>
        new Promise<string>((_resolve, reject) => {
          rejectOld = reject
        }),
    )

    await state.run(() => Promise.resolve('new'))
    rejectOld(new Error('old failure'))
    await old

    expect(state.data.value).toBe('new')
    expect(state.error.value).toBeNull()
    expect(state.pending.value).toBe(false)
  })

  it('exposes non-Error rejections as errors', async () => {
    const state = useAsyncState<string>()

    await state.run(() => Promise.reject('offline'))

    expect(state.error.value).toBeInstanceOf(Error)
    expect(state.error.value?.cause).toBe('offline')
  })
})
