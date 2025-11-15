# Wan 2.1 × ComfyUI Workflows (Text→Image & Image→Image)

This ZIP includes **20 references** (10 for Text→Image and 10 for Image→Image) with direct links to official and community workflows.

> **How to get still images:** Wan 2.1 is a video model. To get a single **image**, set **total frames = 1** (or render a short clip and save the first frame).

---

## Text → Image (via T2V with frames=1)
1. Official Wan2.1 Video Examples — https://docs.comfy.org/tutorials/video/wan/wan-video
2. ComfyUI Examples (Wan page) — https://comfyanonymous.github.io/ComfyUI_examples/wan/
3. ComfyUI‑Wiki: Wan2.1 Complete Guide — https://comfyui-wiki.com/en/tutorial/advanced/video/wan2.1/wan2-1-video-model
4. Fun Control (native) — https://docs.comfy.org/tutorials/video/wan/fun-control
5. VACE (reference aided) — https://docs.comfy.org/tutorials/video/wan/vace
6. LoRA add‑on workflow — https://comfyui-wiki.com/en/tutorial/advanced/video/wan2.1/lora
7. RunComfy (FLF2V sample page) — https://www.runcomfy.com/comfyui-workflows/wan-2-1-flf2v-first-last-frame-video-generation
8. Reddit: community example thread — https://www.reddit.com/r/StableDiffusion/comments/1j209oq/comfyui_wan21_14b_image_to_video_example_workflow/
9. ComfyUI.org overview — https://comfyui.org/en/revolutionize-video-creation-comfyui
10. ATI (Any Trajectory Instruction) site — https://anytraj.github.io/

## Image → Image (via I2V / VACE / Fun / FLF2V)
1. Official Wan2.1 Video Examples — https://docs.comfy.org/tutorials/video/wan/wan-video
2. VACE (reference aided) — https://docs.comfy.org/tutorials/video/wan/vace
3. Fun Control (native) — https://docs.comfy.org/tutorials/video/wan/fun-control
4. FLF2V (First/Last Frame) — https://docs.comfy.org/tutorials/video/wan/wan-flf
5. ComfyUI‑Wiki: Wan2.1 Complete Guide — https://comfyui-wiki.com/en/tutorial/advanced/video/wan2.1/wan2-1-video-model
6. RunComfy FLF2V page — https://www.runcomfy.com/comfyui-workflows/wan-2-1-flf2v-first-last-frame-video-generation
7. ATI site (motion control) — https://anytraj.github.io/
8. ATI GitHub repo — https://github.com/bytedance/ATI
9. Reddit: VACE JSON thread — https://www.reddit.com/r/comfyui/comments/1l10g1o/how_do_i_use_the_latest_wan_21_vace_workflow_ive/
10. Reddit: FLF2V usage — https://www.reddit.com/r/comfyui/comments/1ko6y2b/tried_wan21flf2v14b720p_for_the_first_time/

---

## Model Files (links)
- **Diffusion models:** see ComfyUI Examples page → https://comfyanonymous.github.io/ComfyUI_examples/wan/
- **Text Encoders (UMT5):** usually `umt5_xxl_fp16.safetensors` or `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (see the official pages above)
- **VAE:** `wan_2.1_vae.safetensors`
- **CLIP Vision:** `clip_vision_h.safetensors` (for I2V/VACE/FLF2V)
- **ATI Nodes / WanVideoWrapper:** see https://github.com/bytedance/ATI and notes at https://anytraj.github.io/

> Place models under `ComfyUI/models/diffusion_models/` (and encoders/vae under their respective folders), as indicated on the **ComfyUI Examples** page.

## Usage
- Open any JSON from the linked sources above in ComfyUI.
- For **T2I**, set the Wan **T2V** workflow to 1 frame (or export the first frame).
- For **I2I**, use **I2V/VACE/Fun/FLF2V**, provide your source image, and set frames to 1 for a single image.
- Many example pages include **downloadable JSON** templates. Prefer the **official** ones for stability; community ones can add features.

## Credits & Licenses
- Alibaba Tongyi Wanxiang / Wan2.1 (Apache 2.0)
- ComfyUI project & docs, ComfyUI‑Wiki, community authors (RunComfy, Reddit posts, etc.).
