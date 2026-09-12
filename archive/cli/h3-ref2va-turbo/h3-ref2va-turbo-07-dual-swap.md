---
contract: MiniMaxH3TurboRef2vaInput
width: 960
height: 544
length: 124
seed: null
ref_images: []
ref_videos: []
ref_video_audios: []
ref_audios: []
---

Subject definitions:
- <Subject 1> is the replacement male character shown in <Picture 1>, with front and close-up views treated as one combined identity reference.
- <Subject 2> is the replacement female character shown in <Picture 2>, with front and close-up views treated as one combined identity reference.
- <Video 1> is the source video providing the master performance, scene, camera path, framing, focus, motion blur, lighting, shadows, and original edit.

Summary:
- [video editing + reference generation] The target video is an edited version of <Video 1>. The original male performer is replaced by <Subject 1> and the original female performer is replaced by <Subject 2>, while the original performance, scene, camera movement, framing, focus, motion blur, lighting, shadows, cuts, timing, and audio are preserved. Inherit the original performer's movement, position, pose, rotation, speed, and timing frame by frame. Maintain correct occlusion when the hands and arms pass in front of the body. Do not add new movement, objects, cuts, text, accessories, or camera motion.

Retention analysis:
- <Subject 1>: fully_preserved — face, hair, outfit, colors, body proportions, hands, and visible design details from <Picture 1> are maintained. Keep the face, hair, clothing, hands, and body shape consistent throughout the clip.
- <Subject 2>: fully_preserved — face, hair, outfit, colors, body proportions, hands, and visible design details from <Picture 2> are maintained. Keep the face, hair, clothing, hands, and body shape consistent throughout the clip.
- <Video 1>: fully_preserved — the original movement, position, pose, rotation, speed, timing, background, camera path, framing, focus, motion blur, lighting, shadows, and edit are retained.
