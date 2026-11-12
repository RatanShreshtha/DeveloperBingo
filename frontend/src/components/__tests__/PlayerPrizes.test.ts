import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { PlayerSnapshot } from '../../realtime/protocol'
import PlayerLobbyView from '../../views/PlayerPage.vue'
import { joinedAda, startFresh } from '../../testing/testSetup'

vi.mock('../../api/games', async () => (await import('../../testing/apiMock')).apiGamesMock())

let fake: ReturnType<typeof startFresh>

beforeEach(() => {
  fake = startFresh()
})

// A player in a started game; the server lists the prizes when they join.
function setUpPlayer(overrides: Partial<PlayerSnapshot> = {}) {
  return joinedAda(fake, {
    status: 'started',
    ticket: [['Algorithm', null, 'JSON']],
    prizes: [{ prize: 'early_five', awarded_to: [] }],
    ...overrides,
  })
}

async function mountPlayer() {
  const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })
  await flushPromises()
  return wrapper
}

describe('PlayerLobbyView prizes', () => {
  it('shows draws above prizes and claims in two columns', async () => {
    await setUpPlayer()
    const wrapper = await mountPlayer()

    const headings = wrapper.findAll('h2.card-title')
    expect(headings.slice(0, 3).map((heading) => heading.text())).toEqual(['Draws', 'Prizes', 'Claim'])
    expect(headings[0].element.closest('.grid')).toBeNull()
    expect(headings[1].element.closest('.grid')).toBe(headings[2].element.closest('.grid'))
    expect(headings[1].element.closest('.grid')?.classList.contains('md:grid-cols-2')).toBe(true)
  })

  it('lets the player claim early five', async () => {
    fake.answer('claim_prize', { ok: true, waiting: true })
    await setUpPlayer()
    const wrapper = await mountPlayer()

    await wrapper.get('[data-test="claim-early_five"]').trigger('click')
    await flushPromises()

    expect(fake.payloads('claim_prize')).toEqual([{ prize: 'early_five' }])
  })

  it('shows early five as still open until someone is awarded it', async () => {
    await setUpPlayer()
    const wrapper = await mountPlayer()

    expect(wrapper.text()).toContain('Early five: still open')
  })

  it('hides the claim button until the game starts', async () => {
    await setUpPlayer({ status: 'lobby' })
    const wrapper = await mountPlayer()

    expect(wrapper.find('[data-test="claim-early_five"]').exists()).toBe(false)
  })

  it('shows who early five was awarded to', async () => {
    await setUpPlayer({ prizes: [{ prize: 'early_five', awarded_to: ['Grace'] }] })
    const wrapper = await mountPlayer()

    expect(wrapper.text()).toContain('Early five: awarded to Grace')
  })

  it('updates the board when the room announces an award', async () => {
    await setUpPlayer()
    const wrapper = await mountPlayer()

    fake.emit('prize_awarded', { prize: 'early_five', awarded_to: ['Grace'] })
    await flushPromises()

    expect(wrapper.text()).toContain('Early five: awarded to Grace')
  })

  describe('while a claim waits for its settlement window', () => {
    it('shows the claim as pending until its window settles, then clears it', async () => {
      fake.answer('claim_prize', { ok: true, waiting: true })
      await setUpPlayer()
      const wrapper = await mountPlayer()

      await wrapper.get('[data-test="claim-early_five"]').trigger('click')
      await flushPromises()

      const button = wrapper.get('[data-test="claim-early_five"]')
      expect(button.text()).toBe('Claiming Early five…')
      expect(button.attributes('disabled')).toBeDefined()

      fake.emit('claim_settled', { prize: 'early_five', accepted: true, error: null })
      await flushPromises()

      expect(wrapper.get('[data-test="claim-early_five"]').text()).toBe('Claim Early five')
    })

    it('clears the pending state and shows why when the claim is refused', async () => {
      fake.answer('claim_prize', { ok: false, error: 'claim_not_valid' })
      await setUpPlayer()
      const wrapper = await mountPlayer()

      await wrapper.get('[data-test="claim-early_five"]').trigger('click')
      await flushPromises()

      expect(wrapper.get('[data-test="claim-early_five"]').text()).toBe('Claim Early five')
      expect(wrapper.text()).toContain('This claim does not complete the prize yet')
    })

    it('shows a claim the server still holds as pending after a reload', async () => {
      await setUpPlayer({ pending_claims: ['early_five'] })
      const wrapper = await mountPlayer()

      const button = wrapper.get('[data-test="claim-early_five"]')
      expect(button.text()).toBe('Claiming Early five…')
      expect(button.attributes('disabled')).toBeDefined()

      fake.emit('claim_settled', { prize: 'early_five', accepted: true, error: null })
      await flushPromises()

      expect(wrapper.get('[data-test="claim-early_five"]').text()).toBe('Claim Early five')
    })

    it('explains a tick that cannot be taken back', async () => {
      await setUpPlayer({
        ticks: ['Algorithm'],
        draws: [{ position: 1, name: 'Algorithm', explanation: 'x' }],
      })
      fake.answer('untick_topic', { ok: false, error: 'claim_pending' })
      const wrapper = await mountPlayer()

      await wrapper.get('[data-test="tick-cell"]').trigger('click')
      await flushPromises()

      expect(wrapper.get('[role="alert"]').text()).toContain('claim is waiting')
    })
  })

  it('shows every player a prize was awarded to together', async () => {
    await setUpPlayer({ prizes: [{ prize: 'early_five', awarded_to: ['Ada', 'Grace'] }] })
    const wrapper = await mountPlayer()

    expect(wrapper.text()).toContain('Early five: awarded to Ada, Grace')
  })

  describe('with every prize on the board', () => {
    const labels = {
      top_line: 'Claim Top line',
      middle_line: 'Claim Middle line',
      bottom_line: 'Claim Bottom line',
      four_corners: 'Claim Four corners',
      full_house: 'Claim Full house',
      early_five: 'Claim Early five',
    } as const
    const prizes = Object.keys(labels) as (keyof typeof labels)[]

    async function mountWithFullBoard(awarded: Partial<Record<keyof typeof labels, string[]>> = {}) {
      await setUpPlayer({ prizes: prizes.map((prize) => ({ prize, awarded_to: awarded[prize] ?? [] })) })
      return mountPlayer()
    }

    it('shows a labelled claim button for each prize', async () => {
      const wrapper = await mountWithFullBoard()

      for (const prize of prizes) {
        expect(wrapper.get(`[data-test="claim-${prize}"]`).text()).toBe(labels[prize])
      }
    })

    it.each(prizes)('claims %s by its wire name when its button is clicked', async (prize) => {
      fake.answer('claim_prize', { ok: true, waiting: true })
      const wrapper = await mountWithFullBoard()

      await wrapper.get(`[data-test="claim-${prize}"]`).trigger('click')
      await flushPromises()

      expect(fake.payloads('claim_prize')).toEqual([{ prize }])
    })

    it('disables the button of a prize already awarded', async () => {
      const wrapper = await mountWithFullBoard({ top_line: ['Grace'] })

      expect(wrapper.get('[data-test="claim-top_line"]').attributes('disabled')).toBeDefined()
      expect(wrapper.get('[data-test="claim-middle_line"]').attributes('disabled')).toBeUndefined()
    })
  })
})
