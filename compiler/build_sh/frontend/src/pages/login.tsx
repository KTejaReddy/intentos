// @ts-nocheck
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/apis'
import { go } from '../routes'
import { toast } from '../components/widgets'

export default function loginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
  return (
        <label className='field'>{"Email"}<input type="text" value={email} onChange={e => setEmail(e.target.value)} placeholder="" /></label>
        <label className='field'>{"Password"}<input type="text" value={password} onChange={e => setPassword(e.target.value)} placeholder="" /></label>
  )
}
