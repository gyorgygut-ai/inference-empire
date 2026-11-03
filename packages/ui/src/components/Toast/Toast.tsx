import type { ToastMessage } from "../../hooks/useMessageQueue"

type ToastProps = {
  messages: ToastMessage[]
  onRemove: (message: ToastMessage) => void
}

export const Toast = ({ messages, onRemove }: ToastProps) => {
  if (messages.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className="bg-red-500 text-white px-4 py-2 rounded shadow-lg flex justify-between items-center"
        >
          <span>{msg.text}</span>
          <button
            onClick={() => onRemove(msg)}
            className="ml-4 font-bold"
            aria-label="Close toast"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}