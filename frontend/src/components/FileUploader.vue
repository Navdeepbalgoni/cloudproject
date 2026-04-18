<template>
  <q-page>
    <div class="uploader-container">
      <q-uploader
        ref="uploader"
        @finish="finished"
        label="Add an .mp4 file"
        auto-upload
        extensions=".mp4"
        :factory="uploadVideo"
        :filter="checkFileType"
        @rejected="onRejected"
      />
    </div>

    <q-table
      :loading="loading"
      class="q-mx-lg"
      hide-pagination
      title="My uploads"
      :data="uploadsData"
      :columns="columns"
      row-key="name"
      loading-label="Loading..."
      no-results-label="No results found"
      no-data-label="You haven't sent any files yet"
    >
        <template v-slot:body-cell-download="props">
        <q-td :props="props">
          <q-btn :disable="!props.value" @click="downloadFile(props.value, props.row.video_name)" round color="secondary" icon="cloud_download" />
        </q-td>
      </template>
      <template v-slot:body-cell-download_srt="props">
        <q-td :props="props">
          <q-btn :disable="!props.value" @click="downloadFile(props.value, props.row.video_name.split('.')[0] + '.srt')" round color="primary" icon="description" />
        </q-td>
      </template>
      <template v-slot:body-cell-delete="props">
        <q-td :props="props">
          <q-btn @click="onDelete(props.row.video_id)" round color="red" icon="delete" />
        </q-td>
      </template>
    </q-table>
  </q-page>
</template>

<script>
import videoService from '../service/videoService'
import authService from '../service/authService'

const ALLOWED_FILE_TIPES = ['video/mp4']
export default {
  data () {
    return {
      uploadsData: [],
      loading: false,
      columns: [
        {
          label: 'Name',
          field: 'video_name',
          required: true,
          align: 'left',
          sortable: true
        },
        {
          name: 'duration',
          label: 'Duration',
          field: 'duration',
          sortable: true,
          format: (val) => this.formatTime(val)
        },
        {
          label: 'Status',
          field: 'finished',
          sortable: true,
          format: (val) => val === 'True' ? 'Finished' : 'In progress'
        },
        { label: 'Video', field: 'video_uri', name: 'download' },
        { label: 'SRT', field: 'srt_uri', name: 'download_srt' },
        { label: 'Delete', field: 'video_id', name: 'delete' }
      ]

    }
  },
  methods: {
    checkFileType (files) {
      return files.filter((file) => ALLOWED_FILE_TIPES.includes(file.type))
    },
    onRejected (rejectedEntries) {
      this.$q.notify({
        type: 'negative',
        message: 'Invalid file type'
      })
    },
    formatTime (duration) {
      if (duration) { return duration >= 60 ? `${duration / 60} min` : `${duration} s` }
      return ''
    },
    async uploadVideo (files) {
      try {
        const file = files[0]
        const { attributes } = await authService.getCurrentUser()

        const formData = new FormData()
        formData.set('file_name', file.name)
        formData.set('user_id', attributes.sub)
        formData.set('user_email', attributes.email)
        formData.append('file', file)

        await videoService.send(formData)
        this.$q.notify({
          type: 'positive',
          message: 'Video sent successfully'
        })
      } catch {
        this.$q.notify({
          type: 'negative',
          message: 'Error sending file'
        })
      } finally {
        this.listUploads()
      }
    },
    async listUploads () {
      try {
        this.loading = true
        const { attributes } = await authService.getCurrentUser()
        this.uploadsData = await videoService.list(attributes.sub)
      } catch (err) {
        this.$q.notify({
          type: 'negative',
          message: 'Error loading uploads list'
        })
      } finally {
        this.loading = false
      }
    },
    async onDelete (videoId) {
      try {
        const { attributes } = await authService.getCurrentUser()
        await videoService.remove(attributes.sub, videoId)
        this.$q.notify({
          type: 'positive',
          message: 'Video deleted successfully'
        })
        this.listUploads()
      } catch (err) {
        this.$q.notify({
          type: 'negative',
          message: 'Error deleting video'
        })
      }
    },
    finished () {
      this.$refs.uploader.reset()
    },
    async downloadFile (url, fileName) {
      try {
        const response = await fetch(url)
        const blob = await response.blob()
        const blobUrl = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = blobUrl
        link.download = fileName
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(blobUrl)
      } catch (error) {
        console.error('Download failed', error)
        window.open(url, '_blank')
      }
    }
  },
  created () {
    this.listUploads()
  }
}
</script>

<style lang="stylus" scoped>
.uploader-container {
  padding: 80px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
