<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          @click="leftDrawerOpen = !leftDrawerOpen"
        />
        <q-toolbar-title>Shark Subtitles</q-toolbar-title>
        <q-btn flat dense round icon="logout" />
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="leftDrawerOpen"
      show-if-above
      bordered
      :width="250"
      content-class="bg-grey-1"
    >
      <q-list>
        <q-item
          v-for="(menuItem, index) in menuLinks"
          :key="index"
          clickable
          :active="index == activeIndex"
          @click="setActive(index)"
        >
          <q-item-section avatar>
            <q-icon :name="menuItem.icon" />
          </q-item-section>
          <q-item-section>{{ menuItem.label }}</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>
    <q-page-container>
      <FileUploader v-if="activeIndex == 0" />
    </q-page-container>
  </q-layout>
</template>

<script>
const menuList = [
  {
    icon: 'home',
    label: 'Home'
  },
  {
    icon: 'account_box',
    label: 'Profile',
    separator: true
  },
  {
    icon: 'info',
    label: 'About'
  }
]

import FileUploader from '../components/FileUploader'
export default {
  components: { FileUploader },
  data () {
    return {
      leftDrawerOpen: false,
      menuLinks: menuList,
      activeIndex: 0
    }
  },
  methods: {
    setActive (idx) {
      this.activeIndex = idx
    }
  }
}
</script>
