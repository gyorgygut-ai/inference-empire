import React from "react"
import Image from "next/image"
import hero from "@/public/hero/face_value_hero_0.png"

export const HeroImage = () => (
  <Image
    src={hero}
    alt="Face Value Hero Image"
    style={{ width: "100%", height: "auto" }}
    priority
  />
)

export default HeroImage