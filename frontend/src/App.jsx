import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { Button } from "@/components/ui/button"


export default function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 text-white gap-4">
      <h1 className="text-4xl font-bold">shadcn/ui Test 🧱</h1>
      <Button>Click Me</Button>
    </div>
  )
}
