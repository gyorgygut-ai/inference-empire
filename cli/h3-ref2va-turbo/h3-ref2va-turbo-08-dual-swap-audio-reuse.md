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

<Subject 1> is the man in <Picture 1>, with the front view and close-up views in that reference treated as one combined identity reference; follow his face, hair, outfit, colors, body proportions, hands, and visible design details.

<Subject 2> is the woman in <Picture 2>, with the front view and close-up views in that reference treated as one combined identity reference; follow her face, hair, outfit, colors, body proportions, hands, and visible design details.

<Video 1> is the source video for the target video edit and provides the master performance, scene, camera path, framing, focus, motion blur, lighting, shadows, original edit, and audio.

<Audio 1> is the synchronized audio track of <Video 1> and is reused in the target video.

summary:

[video editing + audio reuse] The target video is an edited version of <Video 1>. The original male and female performers are replaced by <Subject 1> and <Subject 2>, while the original performance, scene, camera movement, framing, focus, motion blur, lighting, shadows, cuts, timing, and audio are preserved. <Audio 1> is reused as the complete final audio track.

retention_analysis:

<Subject 1> (appears wherever the original male performer appears): fully_preserved - his face, hair, outfit, colors, body proportions, hands, and visible design details from <Picture 1> are maintained, using its front and close-up views as one identity reference.

<Subject 2> (appears wherever the original female performer appears): fully_preserved - her face, hair, outfit, colors, body proportions, hands, and visible design details from <Picture 2> are maintained, using its front and close-up views as one identity reference.

<Video 1> (master performance, scene, camera, cut structure, and audio source): fully_preserved - the original movement, position, pose, rotation, speed, timing, background, camera path, framing, focus, motion blur, lighting, shadows, and edit are retained.

<Audio 1>: fully_copy - <Audio 1> is reused 1:1 as the target video's complete final audio track.

detailed_description:

The target video is a direct character-replacement edit of <Video 1>, preserving the original scene, lighting, camera language, edit, and audio while replacing only the identities of the male and female performers.

[Shot 1] In the opening shot of <Video 1>, retain the original background, set, camera path, framing, focus, motion blur, lighting, shadows, and any visible text. Replace the original man with <Subject 1> and the original woman with <Subject 2>. Each replacement inherits the original performer's head orientation, body position, pose, rotation, speed, timing, gaze, expression, mouth motion, hand motion, and arm trajectory frame by frame. <Subject 1> keeps the male face, hair, outfit, colors, body proportions, hands, and visible design details shown in <Picture 1>, treating the front and close-up views as one combined identity reference. <Subject 2> keeps the female face, hair, outfit, colors, body proportions, hands, and visible design details shown in <Picture 2>, treating the front and close-up views as one combined identity reference. Maintain correct occlusion when hands or arms pass in front of the body, and keep body shape, clothing boundaries, and hair consistent across the shot.

[Shot 2] At each remaining shot of <Video 1>, apply the same replacement and preservation constraints. Keep the original cut points, shot length, camera motion, framing, focus, motion blur, background, lighting, and shadows. Do not add new movement, objects, accessories, text, cuts, or camera motion. Where a character is close-up, profile, partially visible, occluded, or in motion, retain the source performance and apply the corresponding identity from <Subject 1> or <Subject 2>. The identity must remain stable across close-ups, front views, side views, and all visible body parts. The original audio from <Audio 1>, including any speech, ambience, and sound effects, is retained unchanged across the entire edit.

overall_soundscape:

The copied ambience, room tone, physical sounds, and any original audio layers from <Audio 1> continue throughout the target video. No new sound is added, removed, replaced, or altered.

non_diegetic_music:

No new non-diegetic music is added. If <Video 1> contains an audience-only score, it is retained as part of <Audio 1>.
