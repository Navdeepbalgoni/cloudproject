// import api from './api'
import { Auth } from 'aws-amplify'

const getCurrentUser = async () => {
  return await Auth.currentUserInfo()
}

const signIn = async (userInfo) => {
  const { username, password } = userInfo
  console.log('[DEBUG] Attempting signIn with username:', username, '| password length:', password.length)
  try {
    const user = await Auth.signIn(username, password)
    console.log('[DEBUG] signIn success:', user)
    return user
  } catch (error) {
    console.log('error signing in', error)
    throw error
  }
}

const signOut = async () => {
  try {
    await Auth.signOut()
  } catch (error) {
    console.log('error signing out: ', error)
    throw error
  }
}

const signUp = async (userInfo) => {
  const { username, password, name } = userInfo
  try {
    const { user } = await Auth.signUp({
      username,
      password,
      attributes: {
        name,
        email: username
      }
    })
    console.log(user)
  } catch (error) {
    console.log('error signing up:', error)
    throw error
  }
}

export default {
  getCurrentUser,
  signIn,
  signOut,
  signUp
}
