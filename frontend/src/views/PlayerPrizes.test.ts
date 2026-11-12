import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { claimPrize, untickTopic } from '../realtime/socket'
import { useLobbyStore } from '../stores/lobby'
import PlayerLobbyView from './PlayerLobbyView.vue'

vi.mock('../api/games', async () => (await import('../testing/apiMock')).apiGamesMock())
vi.mock('../realtime/socket', async () => (await import('../testing/socketMock')).socketModuleMock())

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(claimPrize).mockReset()
})

function setUpPlayer() {
  const store = useLobbyStore()
  store.player = { code: 'ABC123', name: 'Ada' }
  store.ticket = [['Algorithm', null, 'JSON']]
  store.started = true
  // The server lists the prizes when the player joins.
  store.prizes = [{ prize: 'early_five', awarded_to: [] }]
  return store
}

describe('PlayerLobbyView prizes', () => {
  it('lets the player claim early five', async () => {
    vi.mocked(claimPrize).mockResolvedValue({ ok: true })
    setUpPlayer()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    await wrapper.get('[data-test="claim-early_five"]').trigger('click')
    await flushPromises()

    expect(claimPrize).toHaveBeenCalledWith('early_five')
  })

  it('shows early five as still open until someone is awarded it', () => {
    setUpPlayer()
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Early five: still open')
  })

  it('hides the claim button until the game starts', () => {
    const store = setUpPlayer()
    store.started = false
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.find('[data-test="claim-early_five"]').exists()).toBe(false)
  })

  it('shows who early five was awarded to', () => {
    const store = setUpPlayer()
    store.prizes = [{ prize: 'early_five', awarded_to: ['Grace'] }]
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

    expect(wrapper.text()).toContain('Early five: awarded to Grace')
  })

  describe('while a claim waits for its settlement window', () => {
    it('shows the claim as pending until the server answers, then clears it', async () => {
      let settle: (ack: { ok: true }) => void = () => {}
      vi.mocked(claimPrize).mockReturnValue(new Promise((resolve) => (settle = resolve)))
      setUpPlayer()
      const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

      await wrapper.get('[data-test="claim-early_five"]').trigger('click')

      const button = wrapper.get('[data-test="claim-early_five"]')
      expect(button.text()).toBe('Claiming Early five…')
      expect(button.attributes('disabled')).toBeDefined()

      settle({ ok: true })
      await flushPromises()

      expect(wrapper.get('[data-test="claim-early_five"]').text()).toBe('Claim Early five')
    })

    it('clears the pending state and shows why when the claim is refused', async () => {
      vi.mocked(claimPrize).mockResolvedValue({ ok: false, error: 'claim_not_valid' })
      setUpPlayer()
      const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

      await wrapper.get('[data-test="claim-early_five"]').trigger('click')
      await flushPromises()

      expect(wrapper.get('[data-test="claim-early_five"]').text()).toBe('Claim Early five')
      expect(wrapper.text()).toContain('This claim does not complete the prize yet')
    })

    it('explains a draw held for a window and a tick that cannot be taken back', async () => {
      const store = setUpPlayer()
      store.ticks = ['Algorithm']
      store.ticket = [['Algorithm', null, 'JSON']]
      store.draws = [{ position: 1, name: 'Algorithm', explanation: 'x' }]
      vi.mocked(untickTopic).mockResolvedValue({ ok: false, error: 'claim_pending' })
      const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

      await wrapper.get('[data-test="tick-cell"]').trigger('click')
      await flushPromises()

      expect(wrapper.get('[role="alert"]').text()).toContain('claim is waiting')
    })
  })

  it('shows every player a prize was awarded to together', () => {
    const store = setUpPlayer()
    store.prizes = [{ prize: 'early_five', awarded_to: ['Ada', 'Grace'] }]
    const wrapper = mount(PlayerLobbyView, { props: { code: 'ABC123' } })

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

    function mountWithFullBoard(awarded: Partial<Record<keyof typeof labels, string[]>> = {}) {
      const store = setUpPlayer()
      store.prizes = prizes.map((prize) => ({ prize, awarded_to: awarded[prize] ?? [] }))
      return mount(PlayerLobbyView, { props: { code: 'ABC123' } })
    }

    it('shows a labelled claim button for each prize', () => {
      const wrapper = mountWithFullBoard()

      for (const prize of prizes) {
        expect(wrapper.get(`[data-test="claim-${prize}"]`).text()).toBe(labels[prize])
      }
    })

    it.each(prizes)('claims %s by its wire name when its button is clicked', async (prize) => {
      vi.mocked(claimPrize).mockResolvedValue({ ok: true })
      const wrapper = mountWithFullBoard()

      await wrapper.get(`[data-test="claim-${prize}"]`).trigger('click')
      await flushPromises()

      expect(claimPrize).toHaveBeenCalledWith(prize)
    })

    it('disables the button of a prize already awarded', () => {
      const wrapper = mountWithFullBoard({ top_line: ['Grace'] })

      expect(wrapper.get('[data-test="claim-top_line"]').attributes('disabled')).toBeDefined()
      expect(wrapper.get('[data-test="claim-middle_line"]').attributes('disabled')).toBeUndefined()
    })
  })
})
