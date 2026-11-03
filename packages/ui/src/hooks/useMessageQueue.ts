import { useState } from "react"

export type ToastMessage = { id: number; text: string }

export const useMessageQueue = () => {
  const [messages, setMessages] = useState<ToastMessage[]>([])

  const addMessage = (text: string) => {
    setMessages([...messages, { id: Date.now(), text }])
  }

  const removeMessage = (message: ToastMessage) => {
    const index = messages.indexOf(message)
    if (index === -1) return
    setMessages([...messages.slice(0, index), ...messages.slice(index + 1)])
  }

  return { messages, addMessage, removeMessage }
}