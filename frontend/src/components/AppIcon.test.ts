import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AppIcon from './AppIcon.vue'
import { ICONS, type IconName } from './icons'

describe('AppIcon', () => {
  it('is hidden from assistive technology, because the text beside it says what it does', () => {
    const svg = mount(AppIcon, { props: { name: 'plus' } }).get('svg')

    expect(svg.attributes('aria-hidden')).toBe('true')
    expect(svg.attributes('focusable')).toBe('false')
  })

  it('draws the shapes of the named icon', () => {
    const sun = mount(AppIcon, { props: { name: 'sun' } })

    // The sun is a disc with its rays drawn as one path.
    expect(sun.findAll('circle')).toHaveLength(1)
    expect(sun.findAll('path')).toHaveLength(1)
  })

  it('has a drawing for every icon name, so none renders empty', () => {
    for (const name of Object.keys(ICONS) as IconName[]) {
      expect(ICONS[name].length, name).toBeGreaterThan(0)
    }
  })
})
