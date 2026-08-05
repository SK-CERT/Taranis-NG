import { describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot /></div>'
}

const EditorStub = {
    name: 'Editor',
    props: ['modelValue', 'readonly'],
    emits: ['text-change'],
    template: '<button class="editor" @click="$emit(\'text-change\')" />'
}

const mountDialog = (newsItem) =>
    mountWithPlugins(NewsItemDetailDialog, {
        props: { newsItem },
        global: {
            stubs: {
                VDialog: VDialogStub,
                Editor: EditorStub,
                AssessItemActions: true,
                NewsItemAttribute: true
            }
        }
    })

describe('Assess item modify restrictions', () => {
    it('does not advertise aggregate-only comments for a child news item', () => {
        const wrapper = mountDialog({
            id: 7,
            entityType: 'news_item',
            modify: false,
            news_items: [{ news_item_data: { title: 'Read-only child' } }]
        })

        try {
            const tabValues = wrapper.findAllComponents({ name: 'VTab' }).map((tab) => tab.props('value'))
            expect(tabValues).toEqual(['source', 'attributes'])
            expect(wrapper.findComponent({ name: 'Editor' }).exists()).toBe(false)
        } finally {
            wrapper.unmount()
        }
    })

    it('does not apply child ACL flags to aggregate editing', async () => {
        const wrapper = mountDialog({
            id: 8,
            title: 'Locked aggregate',
            description: 'Locked description',
            news_items: [{ id: 1 }, { id: 2 }]
        })

        try {
            expect(wrapper.findComponent({ name: 'VTextField' }).props('readonly')).toBe(false)
            expect(wrapper.findComponent({ name: 'VTextarea' }).props('readonly')).toBe(false)
            expect(wrapper.findComponent({ name: 'Editor' }).props('readonly')).toBe(false)
        } finally {
            wrapper.unmount()
        }
    })
})
