"use client"

import {
  useRef,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react"

type Position = {
  x: number
  y: number
}

type DragSession = Position & {
  pointerId: number
  clientX: number
  clientY: number
  moved: boolean
}

type DraggableProps = {
  children: ReactNode
  label: string
  pressed: boolean
  onClick: () => void
  initialPosition?: Position
}

const constrainPosition = (element: HTMLButtonElement, position: Position) => {
  const { width, height } = element.getBoundingClientRect()
  const maxX = Math.max(0, (window.innerWidth - width) / 2)
  const maxY = Math.max(0, (window.innerHeight - height) / 2)

  return {
    x: Math.min(maxX, Math.max(-maxX, position.x)),
    y: Math.min(maxY, Math.max(-maxY, position.y)),
  }
}

const setPosition = (element: HTMLButtonElement, position: Position) => {
  element.style.transform =
    `translate3d(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px), 0)`
}

export const Draggable = ({
  children,
  label,
  pressed,
  onClick,
  initialPosition = { x: 0, y: 48 },
}: DraggableProps) => {
  const position = useRef<Position>(initialPosition)
  const dragSession = useRef<DragSession | null>(null)
  const suppressClick = useRef(false)

  const onPointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0 || dragSession.current) return

    suppressClick.current = false
    event.currentTarget.setPointerCapture(event.pointerId)
    dragSession.current = {
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      moved: false,
      ...position.current,
    }
  }

  const onPointerMove = (event: PointerEvent<HTMLButtonElement>) => {
    const session = dragSession.current
    if (!session || session.pointerId !== event.pointerId) return

    const deltaX = event.clientX - session.clientX
    const deltaY = event.clientY - session.clientY
    if (!session.moved && Math.hypot(deltaX, deltaY) < 6) return
    session.moved = true

    position.current = constrainPosition(event.currentTarget, {
      x: session.x + deltaX,
      y: session.y + deltaY,
    })
    setPosition(event.currentTarget, position.current)
  }

  const finishPointer = (event: PointerEvent<HTMLButtonElement>) => {
    const session = dragSession.current
    if (!session || session.pointerId !== event.pointerId) return

    suppressClick.current = session.moved
    dragSession.current = null

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const onButtonClick = () => {
    if (suppressClick.current) {
      suppressClick.current = false
      return
    }

    onClick()
  }

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const step = event.shiftKey ? 40 : 12
    let delta: Position | undefined

    if (event.key === "ArrowLeft") delta = { x: -step, y: 0 }
    else if (event.key === "ArrowRight") delta = { x: step, y: 0 }
    else if (event.key === "ArrowUp") delta = { x: 0, y: -step }
    else if (event.key === "ArrowDown") delta = { x: 0, y: step }

    if (!delta) return

    event.preventDefault()
    position.current = constrainPosition(event.currentTarget, {
      x: position.current.x + delta.x,
      y: position.current.y + delta.y,
    })
    setPosition(event.currentTarget, position.current)
  }

  return (
    <button
      type="button"
      className="absolute left-1/2 top-1/2 z-10 cursor-grab touch-none select-none rounded-full bg-transparent p-0 active:cursor-grabbing focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
      style={{
        transform: `translate3d(calc(-50% + ${position.current.x}px), calc(-50% + ${position.current.y}px), 0)`,
      }}
      aria-label={label}
      aria-pressed={pressed}
      onClick={onButtonClick}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={finishPointer}
      onPointerCancel={finishPointer}
      onKeyDown={onKeyDown}
    >
      {children}
    </button>
  )
}

export default Draggable