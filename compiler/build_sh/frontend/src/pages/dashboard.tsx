// @ts-nocheck
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/apis'
import { go } from '../routes'
import { toast } from '../components/widgets'

export default function dashboardPage() {
  return (
    <div className='page empty'>No widgets yet</div>
  )
}
