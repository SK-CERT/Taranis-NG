export type Id = string | number

export type AssetCpe = { value: string }

export type ReportAttribute = {
    id?: number | null
    attribute_group_item_title?: string | null
    value?: string | null
    value_description?: string | null
}

export type VulnerabilityReport = {
    id: number
    title?: string
    subtitle?: string
    created?: string
    last_updated?: string
    attributes?: ReportAttribute[]
}

export type AssetVulnerability = {
    solved: boolean
    report_item: VulnerabilityReport
}

export type Asset = {
    id: number
    name: string
    serial: string
    description: string
    asset_group_id: string
    asset_cpes: AssetCpe[]
    vulnerabilities_count?: number
    vulnerabilities?: AssetVulnerability[]
    title?: string
    subtitle?: string
    tag?: string
}

export type UserReference = { id: Id; username?: string; name?: string }
export type TemplateReference = { id: Id; name?: string; description?: string }

export type AssetGroup = {
    id: string
    name: string
    description: string
    users?: UserReference[]
    templates?: TemplateReference[]
    title?: string
    subtitle?: string
}

export type NotificationRecipient = { id?: number; email: string; name: string }

export type NotificationTemplate = {
    id: number
    name: string
    description: string
    message_title: string
    message_body: string
    recipients: NotificationRecipient[]
    title?: string
    subtitle?: string
}

export type ListResponse<T> = { total_count: number; items: T[] }

export type AssetFilter = {
    search: string
    vulnerable: boolean
    sort: 'ALPHABETICAL' | 'VULNERABILITY'
}
