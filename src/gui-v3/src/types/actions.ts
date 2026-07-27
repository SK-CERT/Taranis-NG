// uppercase strings because some actions are send and compared on the python side...
export const Action = {
    AGGREGATE_OPEN: 'AGGREGATE-OPEN',
    COMMENT: 'COMMENT',
    CREATE_REPORT: 'CREATE-REPORT',
    DELETE: 'DELETE',
    DISLIKE: 'DISLIKE',
    GROUP: 'GROUP',
    IMPORTANT: 'IMPORTANT',
    LIKE: 'LIKE',
    OPEN: 'OPEN',
    READ: 'READ',
    UNGROUP: 'UNGROUP',
    UPDATE_AGGREGATE: 'UPDATE-AGGREGATE'
} as const

export type ActionKey = (typeof Action)[keyof typeof Action]
