'use server'

import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export async function login(_: unknown, formData: FormData) {
  const password = formData.get('password') as string

  if (!password || password !== process.env.ADMIN_PASSWORD) {
    return { error: 'Invalid password' }
  }

  cookies().set('admin_token', password, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7,
    path: '/',
  })

  redirect('/clients')
}

export async function logout() {
  cookies().delete('admin_token')
  redirect('/login')
}
