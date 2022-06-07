import { getDashboardData } from '@/api/dashboard'
import { getField, updateField } from 'vuex-map-fields'
import { xor } from 'lodash'

import { faker } from '@faker-js/faker'
import moment from 'moment'

const state = {
  dummyTopics: [],
  dummySharingSets: [],
  dummyNewsItems: []
}

const actions = {

  init(context) {
    context.commit('INIT_DUMMYDATA')
  }
  
}

const mutations = {
  
  updateField,
  
  INIT_DUMMYDATA (state) {
    let numberOfDummyTopics = 40
    let numberOfDummySharingSets = 6
    let numberOfDummyNewsItem = 1000
    state.dummyTopics = generateTopics(numberOfDummyTopics, false, 0)
    console.log(state.dummyTopics)
    state.dummyNewsItems = generateNewsItems(numberOfDummyNewsItem, numberOfDummyTopics)
    console.log(state.dummyNewsItems)

    // Assign Items to topics
    state.dummyTopics.forEach(topic => {
      let items = faker.random.arrayElements(
        state.dummyNewsItems,
        topic.items.total
      )
      items.forEach(item => {
        item.topics.push(topic.id)
      })
   });
   
   state.dummySharingSets = generateTopics(numberOfDummySharingSets, true, numberOfDummyTopics)
   console.log(state.dummySharingSets)

   // Assign Items to Sharingsets
   state.dummySharingSets.forEach(sharingSet => {
     let items = faker.random.arrayElements(
       state.dummyNewsItems,
       sharingSet.items.total
     )
     items.forEach(item => {
       item.topics.forEach(topicId => {
         let parentTopic = state.dummyTopics.find(topic => topic.id === topicId)
        //  Set has shared
         parentTopic.hasSharedItems = true;
        //  append sharing set to topic
         if (!parentTopic.sharingSets.includes(sharingSet.id)) {
          parentTopic.sharingSets.push(sharingSet.id);
        }
       })
       item.shared = true
       item.sharingSets.push(sharingSet.id)
     })
  });


  }
}

const getters = {

  getField,

  getDummyTopics (state) {
    return state.dummyTopics
  },
  getDummySharingSets (state) {
    return state.dummySharingSets
  },
  getDummyNewsItems (state) {
    return state.dummyNewsItems
  },

}

export const dummyData = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}

// -------------------------------------------------------

var dummyTags = [
  { label: 'State', color: 1 },
  { label: 'Cyberwar', color: 2 },
  { label: 'Threat', color: 3 },
  { label: 'DDoS', color: 4 },
  { label: 'Vulnerability', color: 5 },
  { label: 'Java', color: 6 },
  { label: 'CVE', color: 7 },
  { label: 'OT/CPS', color: 8 },
  { label: 'Python', color: 9 },
  { label: 'Privacy', color: 10 },
  { label: 'Social', color: 11 },
  { label: 'APT', color: 12 },
  { label: 'MitM', color: 13 }
]

var dummySourceTypes = [
  'RSS',
  'MISP',
  'Web',
  'Twitter',
  'Email',
  'Slack',
  'Atom'
]

function generateTopics(numberOfDummyTopics, sharingSet, offset) {

  let dummyData = []

  for (let i = 1; i < numberOfDummyTopics; i++) {
    let entry = {
      id: i + offset,
      relevanceScore: parseInt(faker.commerce.price(0, 100, 0)),
      title: Math.random() < 0.5 ? `${faker.hacker.adjective()} ${faker.hacker.noun()} ${faker.hacker.abbreviation()}` : `${faker.hacker.adjective()} ${faker.hacker.noun()} ${faker.hacker.noun()}`,
      tags: faker.random.arrayElements(
        dummyTags,
        Math.floor(Math.random() * (5 - 2 + 1)) + 2
      ),
      ai: Math.random() < 0.25,
      hot: Math.random() < 0.15,
      pinned: Math.random() < 0.05,
      lastActivity: new Date(String(faker.date.recent(10))),
      excerpt: faker.lorem.paragraph(30),
      items: {
        total: sharingSet ? parseInt(faker.commerce.price(6, 16, 0)) : parseInt(faker.commerce.price(40, 80, 0)),
        new: parseInt(faker.commerce.price(0, 6, 0))
      },
      comments: {
        total: parseInt(faker.commerce.price(20, 40, 0)),
        new: parseInt(faker.commerce.price(0, 40, 0))
      },
      votes: {
        up: parseInt(faker.commerce.price(0, 50, 0)),
        down: parseInt(faker.commerce.price(0, 50, 0))
      },
      hasSharedItems: false,
      isSharingSet: sharingSet,
      sharingSets: [],
      relatedTopics: [],
      keywords: faker.random
        .words(Math.random() * (16 - 6 + 1) + 6)
        .split(' '),
      selected: false
    }

    if (!sharingSet) {
      // Add related topics
      for (let i = 1; i < Math.floor(Math.random() * (4)); i++) {
        let newTopicLink = Math.floor(Math.random() * (numberOfDummyTopics))
        if (!entry.relatedTopics.includes(newTopicLink)) {
          entry.relatedTopics.push(newTopicLink)
        }
      }
    }

    dummyData.push(entry)
  }

  return dummyData
}

function generateNewsItems (numberOfDummyNewsItem, numberOfDummyTopics) {

  var dummyData = []

  for (var i = 1; i < numberOfDummyNewsItem; i++) {
    var sourceDomain = faker.internet.domainName()
    var entry = {
      id: i,
      relevanceScore: faker.commerce.price(0, 100, 0),
      title: faker.hacker.phrase(),
      excerpt: faker.lorem.paragraph(100),
      tags: faker.random.arrayElements(
        dummyTags,
        Math.floor(Math.random() * (5 - 2 + 1)) + 2
      ),
      published: new Date(String(faker.date.recent(80))),
      collected: new Date(String(faker.date.recent(20))),
      source: {
        domain: sourceDomain,
        url: `${faker.internet.protocol()}://${sourceDomain}/rss/${moment(
          new Date(String(faker.date.recent(50)))
        ).format('YYYY/MM/DD')}/${faker.internet.password(20)}`,
        type: dummySourceTypes[Math.floor(Math.random() * 7)]
      },
      addedBy: faker.lorem.words(1),
      topics: [],
      votes: {
        up: parseInt(faker.commerce.price(0, 50, 0)),
        down: parseInt(faker.commerce.price(0, 50, 0))
      },
      important: Math.random() < 0.2,
      read: Math.random() < 0.2,
      decorateSource: Math.random() < 0.2,
      recommended: Math.random() < 0.2,
      inAnalysis: Math.random() < 0.2,
      shared: false,
      sharingSets: [],
      restricted: Math.random() < 0.2,
      selected: false
    }

    dummyData.push(entry)
  }

  return dummyData
}