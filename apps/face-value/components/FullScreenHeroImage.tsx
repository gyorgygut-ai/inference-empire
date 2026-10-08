import Image from "next/image"

export default function FullScreenHeroImage() {
  return (
    <Image
      src="/images/face_value_hero_0.png"
      fill
      alt="Face Value Hero Image"
      style={{ objectFit: "cover" }}
      priority
    />
  )
}