import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import GroupNavList from '@/components/common/GroupNavList.vue'
import AssessNav from '@/views/nav/AssessNav.vue'
import { getAllOSINTSourceGroupsAssess, getUnreadCountsByGroup } from '@/api/assess'

/**
 * The Assess rail shows how many news items in each OSINT source group nobody has read yet,
 * and keeps the numbers current as items are collected, read or deleted.
 */

vi.mock('@/api/assess', () => ({
    getAllOSINTSourceGroupsAssess: vi.fn(),
    getUnreadCountsByGroup: vi.fn()
}))

vi.mock('vue-router', () => ({
    useRouter: () => ({ push: vi.fn() }),
    useRoute: () => ({ params: { groupId: 'all' } })
}))

const groups = [
    { id: 'all', icon: 'mdi-folder-multiple', title: 'collectors.groups.all', translate: true, route: '/assess/group/all' },
    { id: 'g1', icon: 'mdi-folder-multiple', title: 'Vulnerabilities', translate: false, route: '/assess/group/g1' },
    { id: 'g2', icon: 'mdi-folder-multiple', title: 'News', translate: false, route: '/assess/group/g2' }
]

const countFor = (wrapper, groupId) => wrapper.find(`[data-group-id="${groupId}"] [data-test="group-unread-count"]`)

let wrapper

afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
})

describe('GroupNavList unread counts', () => {
    it('shows the unread count after a group, and nothing for a group with none', () => {
        wrapper = mountWithPlugins(GroupNavList, { props: { groups, unreadCounts: { all: 12, g1: 12 } } })

        expect(countFor(wrapper, 'all').text()).toBe('12')
        expect(countFor(wrapper, 'g1').text()).toBe('12')
        expect(countFor(wrapper, 'g1').attributes('title')).toBe('Unread: 12')
        expect(countFor(wrapper, 'g2').exists()).toBe(false)
    })

    it('gives thousands in short and keeps the exact number in the tooltip', () => {
        wrapper = mountWithPlugins(GroupNavList, { props: { groups, unreadCounts: { all: 12345, g1: 7645, g2: 999 } } })

        expect(countFor(wrapper, 'all').text()).toBe('12k')
        expect(countFor(wrapper, 'all').attributes('title')).toBe('Unread: 12,345')
        expect(countFor(wrapper, 'g1').text()).toBe('7.6k')
        expect(countFor(wrapper, 'g2').text()).toBe('999')
    })

    it('shows no counts when none are given', () => {
        wrapper = mountWithPlugins(GroupNavList, { props: { groups } })

        expect(wrapper.find('[data-test="group-unread-count"]').exists()).toBe(false)
    })
})

describe('AssessNav unread counts', () => {
    beforeEach(() => {
        vi.useFakeTimers()
        getAllOSINTSourceGroupsAssess.mockResolvedValue({ data: { total_count: 1, items: [{ id: 'g1', name: 'Vulnerabilities' }] } })
        getUnreadCountsByGroup.mockReset()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    const mountNav = async () => {
        wrapper = mountWithPlugins(AssessNav)
        await flushPromises()
    }

    it('loads the counts with the groups', async () => {
        getUnreadCountsByGroup.mockResolvedValue({ data: { all: 7, g1: 7 } })

        await mountNav()

        expect(countFor(wrapper, 'all').text()).toBe('7')
        expect(countFor(wrapper, 'g1').text()).toBe('7')
    })

    it('reloads the counts once for a burst of news item updates', async () => {
        getUnreadCountsByGroup.mockResolvedValueOnce({ data: { all: 7, g1: 7 } }).mockResolvedValue({ data: { all: 9, g1: 9 } })
        await mountNav()

        for (let event = 0; event < 3; event += 1) {
            window.dispatchEvent(new CustomEvent('news-items-updated'))
        }
        await vi.runAllTimersAsync()
        await flushPromises()

        expect(getUnreadCountsByGroup).toHaveBeenCalledTimes(2)
        expect(countFor(wrapper, 'g1').text()).toBe('9')
    })

    it('stops following updates once it is gone', async () => {
        getUnreadCountsByGroup.mockResolvedValue({ data: { all: 7 } })
        await mountNav()
        wrapper.unmount()
        wrapper = undefined

        window.dispatchEvent(new CustomEvent('news-items-updated'))
        await vi.runAllTimersAsync()

        expect(getUnreadCountsByGroup).toHaveBeenCalledTimes(1)
    })
})
