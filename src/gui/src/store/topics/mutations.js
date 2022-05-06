
import moment from 'moment'

export const mutations = {

    togglePin(state, id) {
        var index = state.topicList.accumulated.findIndex(x => x.id === id)
        state.topicList.accumulated[index].pinned = !state.topicList.accumulated[index].pinned
    },

    toggleSelect(state, id) {
        var index = state.topicList.accumulated.findIndex(x => x.id === id)
        state.topicList.accumulated[index].selected = !state.topicList.accumulated[index].selected
    },


    sortTopics(state) {

        var type = state.sortBy.selected.type
        var direction = state.sortBy.selected.direction
        var keepPinned = state.sortBy.keepPinned

        state.topicList.accumulated.sort((x, y) => {

            // Get properties
            var elements = getElements(type, x, y)

            // Set direction
            elements = (direction === 'asc') ? elements : [elements[1], elements[0]]

            // Apply pinned sorting
            if (keepPinned) {
                if (x.pinned && !y.pinned) return -1
                if (!x.pinned && y.pinned) return 1
            } 

            // Apply property sorting
            return propertySorting(type, elements)
        })
    },

    // Setters
    setDashboardData(state, data) {
        state.dashboard_data = data
    },

    applySortby(state, data) {
        state.sortBy = data
    },

    setTopicList(state, { selector, data }) {
        state.topicList[selector] = data
    },

    setFilterList(state, data) {
        state.filterList = data
    },

    setOriginalTopicList(state, data) {
        state.topicList.original = data
    },

    setAccumulatedTopicList(state, data) {
        state.topicList.accumulated = data
    },

    applyFilter(state, data) {
        state.filter = data
    }

}

function getElements(type, x, y) {
    switch(type) {
        case 'relevanceScore':
            return [x.relevanceScore, y.relevanceScore]
        case 'lastActivity':
            return [x.lastActivity, y.lastActivity]
        case 'newItems':
            return [x.items.new, y.items.new]
        case 'newComments':
            return [x.comments.new, y.comments.new]
        case 'upvotes':
            return [x.votes.up, y.votes.up]
    }
}

function propertySorting(type, elements) {
    if (elements[0] === elements[1]) return 0 
    if (type === 'lastActivity') {
        return moment(elements[0], 'DD/MM/YYYY hh:mm:ss') - moment(elements[1], 'DD/MM/YYYY hh:mm:ss')
    } else {
        return (parseInt(elements[0]) < parseInt(elements[1])) ? -1 : 1
    }
}
