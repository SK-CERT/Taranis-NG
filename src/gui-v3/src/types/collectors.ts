/**
 * The shapes the collectors views pass between each other.
 *
 * These lived twice - once in the OSINT sources view, once in the table component it renders -
 * and drifted: the view still described `collector` as a string and knew nothing of the run
 * state, so passing its own items into the component was a type error between two types of the
 * same name. Declared once here, they cannot disagree again.
 *
 * The index signature stays because both come straight from the API, which carries more fields
 * than either file names. Anything actually read has to be declared above it, or TypeScript
 * requires the bracket form to reach it.
 */

export type OSINTSourceItem = {
    id: string | number
    name?: string
    description?: string
    enabled?: boolean
    /** Live run state, cached by core rather than stored; absent when nothing is known. */
    collecting?: boolean
    next_run?: string | null
    last_attempted?: string | null
    last_collected?: string | null
    last_error_message?: string | null
    status?: string
    collector_id?: string
    collector?: { id?: string; name?: string; type?: string }
    osint_source_groups?: Array<{ id: string | number; name?: string; default?: boolean }>
    [key: string]: unknown
}

export type CollectorsNodeItem = {
    id: string | number
    name?: string
    description?: string
    status?: string
    last_seen?: string
    collectors?: Array<{ id?: string }>
}
