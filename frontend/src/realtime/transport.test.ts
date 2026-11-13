import { describe, expect, it, vi } from 'vitest'

const emitWithAck = vi.fn().mockResolvedValue({ ok: true })
const timeout = vi.fn(() => ({ emitWithAck }))
vi.mock('socket.io-client', () => ({ io: () => ({ timeout }) }))

import { SEND_TIMEOUT_MS, socketIoTransport } from './transport'

describe('the socket.io transport', () => {
  it('sends every command with a reply timeout, so an unreachable server rejects instead of waiting forever', async () => {
    await socketIoTransport().send('end_game', { code: 'ABC123', host_token: 'secret-token' })

    expect(timeout).toHaveBeenCalledWith(SEND_TIMEOUT_MS)
    expect(emitWithAck).toHaveBeenCalledWith('end_game', { code: 'ABC123', host_token: 'secret-token' })
  })
})
