import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import RemoteReportItem from '@/components/analyze/RemoteReportItem.vue'
import RemoteAttributeAttachment from '@/components/common/attribute/RemoteAttributeAttachment.vue'
import { downloadReportItemAttachment, getReportItem } from '@/api/analyze'

vi.mock('@/api/analyze', () => ({
    getReportItem: vi.fn(),
    downloadReportItemAttachment: vi.fn()
}))

const RemoteAttributeContainerStub = {
    name: 'RemoteAttributeContainer',
    props: ['attributeGroup', 'reportItemId'],
    template: '<div class="remote-attribute-stub">{{ attributeGroup.title }}</div>'
}

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div><slot /></div>'
}

describe('RemoteReportItem', () => {
    beforeEach(() => vi.clearAllMocks())

    it('loads an authorized remote report and groups its flat attributes by title and type', async () => {
        getReportItem.mockResolvedValue({
            data: {
                id: 41,
                uuid: 'remote-uuid',
                title: 'Remote report',
                remote_user: 'upstream-node',
                attributes: [
                    { id: 1, attribute_group_item_title: 'Summary', value: 'First' },
                    { id: 2, attribute_group_item_title: 'Summary', value: 'Second' },
                    {
                        id: 3,
                        attribute_group_item_title: 'Evidence',
                        value: 'proof.txt',
                        binary_mime_type: 'text/plain',
                        binary_size: 5
                    }
                ]
            }
        })
        const wrapper = mountWithPlugins(RemoteReportItem, {
            global: { stubs: { VDialog: VDialogStub, RemoteAttributeContainer: RemoteAttributeContainerStub } }
        })

        await wrapper.vm.showDetail({ id: 41, remote_user: 'upstream-node' })
        await flushPromises()

        const groups = wrapper.findAllComponents(RemoteAttributeContainerStub)
        expect(groups).toHaveLength(2)
        expect(groups[0].props('attributeGroup')).toMatchObject({ title: 'Summary', attributeType: 'TEXT' })
        expect(groups[0].props('attributeGroup').attributes).toHaveLength(2)
        expect(groups[1].props('attributeGroup')).toMatchObject({ title: 'Evidence', attributeType: 'ATTACHMENT' })
        expect(groups[1].props('reportItemId')).toBe(41)
    })

    it('refuses to route a local report into the remote viewer', async () => {
        const wrapper = mountWithPlugins(RemoteReportItem, { global: { stubs: { VDialog: VDialogStub } } })

        await wrapper.vm.showDetail({ id: 12, remote_user: null })

        expect(getReportItem).not.toHaveBeenCalled()
        expect(wrapper.find('.remote-report__identity').text()).not.toContain('12')
    })
})

describe('RemoteAttributeAttachment', () => {
    beforeEach(() => vi.clearAllMocks())

    it('downloads from the report-scoped API and never trusts a payload URL', async () => {
        const wrapper = mountWithPlugins(RemoteAttributeAttachment, {
            props: {
                reportItemId: 41,
                attributeGroup: {
                    attributes: [{ id: 3, value: 'proof.txt', binary_size: 5, download_url: 'https://evil.invalid/file' }]
                }
            }
        })

        await wrapper.get('button').trigger('click')

        expect(downloadReportItemAttachment).toHaveBeenCalledWith(41, 3, 'proof.txt')
    })
})
