import api from './api'

const list = async (userid) => {
  const { data: response } = await api.get(`/list?id=${userid}`)
  return response
}

const send = async (data) => {
  const { data: response } = await api.post('/send', data, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })
  return response
}

const remove = async (userid, videoid) => {
  const { data: response } = await api.delete(`/delete?user_id=${userid}&video_id=${videoid}`)
  return response
}

export default {
  list,
  send,
  remove
}
