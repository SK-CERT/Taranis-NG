/* eslint-disable vue/one-component-per-file -- test harness uses minimal inline components */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { computed, defineComponent, h, reactive } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeLink from '@/components/common/attribute/AttributeLink.vue'
import { attributeWriteMark, attributeWritesPending, attributeWritesSince } from '@/components/common/attribute/useAttributes'
import { createLinkReferences, provideLinkReferences } from '@/composables/useLinkReferences'
import { numberLinks } from '@/utils/linkReferences'
import AuthService from '@/services/auth_service'
import { getReportItemData, updateReportItem } from '@/api/analyze'

/**
 * Links edited against a slow core: a user adding, inserting and typing fast, while the report
 * dialog re-reads the report now and then (a resync after the live stream was down).
 *
 * A resync used to replace the list whenever no field had focus - right after a click on "+"
 * too - so it could list a just-added link twice, drop it, or show a link as it was before the
 * text typed into it was saved (and drop that save). It now waits for writes under way and
 * discards what it read before a write began (see NewReportItem.showDetail).
 */

vi.mock('@/api/analyze', () => ({
    getReportItemData: vi.fn(),
    holdLockReportItem: vi.fn().mockResolvedValue({}),
    lockReportItem: vi.fn().mockResolvedValue({}),
    unlockReportItem: vi.fn().mockResolvedValue({}),
    updateReportItem: vi.fn()
}))

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function fakeCore(seed) {
    let random = seed
    const rand = () => {
        random = (random * 1103515245 + 12345) % 2147483648
        return random / 2147483648
    }
    const attributes = new Map()
    let nextId = 100
    let nextKey = 0
    const ensureKeys = () => {
        const seen = new Set()
        for (const attribute of [...attributes.values()].sort((a, b) => a.id - b.id)) {
            if (!attribute.value_description || seen.has(attribute.value_description)) attribute.value_description = `k${nextKey++}`
            seen.add(attribute.value_description)
        }
    }
    const latency = () => sleep(Math.floor(rand() * 15))
    updateReportItem.mockImplementation(async (_id, data) => {
        await latency()
        if (data.add) {
            const attribute = { id: nextId++, value: '', value_description: '', version: 1 }
            attributes.set(attribute.id, attribute)
            ensureKeys()
            return { data: { ...data, attribute_id: attribute.id } }
        }
        if (data.delete) {
            attributes.delete(Number(data.attribute_id))
            return { data }
        }
        if (data.update) {
            const attribute = attributes.get(Number(data.attribute_id))
            if (data.base_version !== undefined && Number(data.base_version) !== attribute.version) {
                const error = new Error('conflict')
                error.response = {
                    status: 409,
                    data: {
                        conflict: {
                            attribute_id: attribute.id,
                            current_version: attribute.version,
                            current_value: attribute.value,
                            current_value_description: attribute.value_description
                        }
                    }
                }
                throw error
            }
            attribute.value = data.attribute_value
            if (data.value_description !== undefined) attribute.value_description = data.value_description
            attribute.version += 1
            return { data: { ...data, attribute_version: attribute.version } }
        }
        return { data }
    })
    getReportItemData.mockImplementation(async (_id, data) => {
        await latency()
        const attribute = attributes.get(Number(data.attribute_id))
        const result = {
            ...data,
            attribute_value: attribute.value,
            attribute_value_description: attribute.value_description,
            attribute_user: 'me'
        }
        if (data.update) result.attribute_version = attribute.version
        return { data: result }
    })
    // The dialog's resync: re-read the report and replace the list (see NewReportItem.showDetail).
    const resync = async (values, guarded) => {
        if (guarded && attributeWritesPending()) return
        const mark = attributeWriteMark()
        const read = [...attributes.values()]
            .sort((a, b) => a.id - b.id)
            .map((attribute, index) => ({ ...attribute, index, locked: false, user: null }))
        await latency()
        if (guarded && (attributeWritesPending() || attributeWritesSince(mark))) return
        values.splice(0, values.length, ...read)
    }
    return { attributes, rand, resync }
}

function mountLinks() {
    const values = reactive([])
    const Form = defineComponent({
        setup() {
            provideLinkReferences(
                createLinkReferences(
                    computed(() => numberLinks(values)),
                    computed(() => []),
                    computed(() => [])
                )
            )
            return () =>
                h(AttributeLink, {
                    edit: true,
                    modify: true,
                    reportItemId: 42,
                    attributeGroup: { id: 12, attribute: { type: 'LINK' }, min_occurrence: 0, max_occurrence: 20 },
                    values
                })
        }
    })
    return { wrapper: mountWithPlugins(Form), values }
}

describe('AttributeLink against a slow core', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        vi.spyOn(AuthService, 'hasPermission').mockReturnValue(true)
    })

    it.each(Array.from({ length: 12 }, (_, seed) => seed + 1))('keeps the rows, the screen and the core in step (seed %i)', async (seed) => {
        const guarded = true
        const { attributes, rand, resync } = fakeCore(seed)
        const { wrapper, values } = mountLinks()
        await flushPromises()
        const pending = []
        for (let step = 0; step < 12; step++) {
            const rows = wrapper.findAll('[data-test="link-row"]')
            const action = rand()
            if (action > 0.85) {
                pending.push(resync(values, guarded))
            } else if (action < 0.35 || rows.length === 0) {
                // "+" at the end
                pending.push(wrapper.get('[data-test="link-add"]').trigger('click'))
            } else if (action < 0.55) {
                // "+" between rows
                const inserts = wrapper.findAll('[data-test="link-insert"]')
                pending.push(inserts[Math.floor(rand() * inserts.length)]?.trigger('click'))
            } else {
                // Type into a row, then leave it
                const inputs = wrapper.findAll('[data-test="link-row"] input')
                const input = inputs[Math.floor(rand() * inputs.length)]
                if (input) {
                    const text = `https://example.test/${seed}-${step}`
                    await input.trigger('focus')
                    await input.setValue(text)
                    pending.push(input.trigger('blur'))
                }
            }
            await sleep(Math.floor(rand() * 10))
        }
        await Promise.all(pending)
        await sleep(400)
        await flushPromises()

        const objects = new Set(values)
        const ids = values.map((value) => value.id)
        expect(objects.size, 'the same object twice').toBe(values.length)
        expect(new Set(ids).size, `duplicate ids ${JSON.stringify(ids)}`).toBe(ids.length)
        expect(values.length, 'rows vs server').toBe(attributes.size)
        for (const value of values) {
            expect(attributes.get(value.id)?.value, `row ${value.id} differs from core`).toBe(value.value)
        }
        // What the user sees: one input per link, each showing its link.
        const shown = wrapper.findAll('[data-test="link-row"] input').map((input) => input.element.value)
        expect(shown, 'rows on screen').toEqual(values.map((value) => String(value.value ?? '')))
        wrapper.unmount()
    })

    it('does not list an added link twice when a resync listed it already', async () => {
        const { attributes } = fakeCore(1)
        const { wrapper, values } = mountLinks()
        await flushPromises()
        const read = getReportItemData.getMockImplementation()
        getReportItemData.mockImplementationOnce(async (id, data) => {
            const answer = await read(id, data)
            // The dialog re-read the report after the core stored the link, before this add listed it.
            values.push({ id: Number(data.attribute_id), index: 0, value: '', value_description: 'k0', version: 1 })
            return answer
        })

        await wrapper.get('[data-test="link-add"]').trigger('click')
        await sleep(50)
        await flushPromises()

        expect(values.map((value) => value.id)).toEqual([...attributes.keys()])
        expect(wrapper.findAll('[data-test="link-row"]')).toHaveLength(1)
    })

    it("lists another user's link once, though two copies of the attribute hear of it", async () => {
        fakeCore(1)
        const values = reactive([])
        const group = { id: 12, attribute: { type: 'LINK' }, min_occurrence: 0, max_occurrence: 20 }
        const Page = defineComponent({
            setup() {
                provideLinkReferences(
                    createLinkReferences(
                        computed(() => numberLinks(values)),
                        computed(() => []),
                        computed(() => [])
                    )
                )
                // The source form and a language tab's read-only copy share the list.
                const common = { edit: true, modify: true, reportItemId: 42, attributeGroup: group, values }
                return () => h('div', [h(AttributeLink, common), h(AttributeLink, { ...common, readOnly: true })])
            }
        })
        const wrapper = mountWithPlugins(Page)
        await flushPromises()
        await updateReportItem(42, { add: true, report_item_id: 42, attribute_id: -1, attribute_group_item_id: 12 })

        window.dispatchEvent(
            new CustomEvent('report-item-updated', {
                detail: { add: true, report_item_id: 42, attribute_group_item_id: 12, attribute_id: 100, user_id: 7 }
            })
        )
        await sleep(50)
        await flushPromises()

        expect(values.map((value) => value.id)).toEqual([100])
        wrapper.unmount()
    })

    it('counts a save as under way from when it is queued until it is done', async () => {
        fakeCore(1)
        const { wrapper } = mountLinks()
        await flushPromises()
        await wrapper.get('[data-test="link-add"]').trigger('click')
        await sleep(50)
        await flushPromises()
        expect(attributeWritesPending()).toBe(false)

        const mark = attributeWriteMark()
        const input = wrapper.get('[data-test="link-row"] input')
        await input.trigger('focus')
        await input.setValue('https://example.test/new')
        await input.trigger('blur')

        expect(attributeWritesPending()).toBe(true)
        expect(attributeWritesSince(mark)).toBe(true)
        await sleep(50)
        await flushPromises()
        expect(attributeWritesPending()).toBe(false)
        wrapper.unmount()
    })
})
