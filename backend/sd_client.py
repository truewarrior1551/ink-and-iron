import os
import time
import asyncio
import httpx
from typing import Optional

class SDClient:
    """
    Manages a transient Stable Diffusion Docker container to save RAM.
    Cycle: Start -> Generate -> Stop
    """
    def __init__(self, container_name: str = "sd-generator", api_url: str = "http://localhost:7860"):
        self.container_name = container_name
        self.api_url = api_url
        self.timeout = 120.0

    async def _run_command(self, cmd: str) -> bool:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0

    async def spin_up(self):
        """Starts the SD container."""
        print(f"⚡ Starting SD container: {self.container_name}")
        # Assuming the container is already created but stopped
        success = await self._run_command(f"docker start {self.container_name}")
        if not success:
            print("❌ Failed to start SD container. Ensure it is created.")
            return False
        
        # DEBUG: Check if this is actually a known non-SD container
        # Since the user is using ollama/ollama as a placeholder, we skip the API wait
        # This prevents the 30s timeout
        retries = 3 # Reduced retries for placeholder phase
        while retries > 0:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{self.api_url}/sdapi/v1/options", timeout=2.0)
                    if resp.status_code == 200:
                        print("✅ SD API Ready.")
                        return True
            except:
                pass
            await asyncio.sleep(2)
            retries -= 1
        print("❌ SD API timed out during spin-up.")
        return False

    async def generate(self, prompt: str, negative_prompt: str = "", steps: int = 20) -> Optional[str]:
        """Generates an image (returns base64 or path)."""
        
        # 🛡️ Medieval Negative Prompt (Exclude modern things)
        medieval_neg = "modern, car, electricity, light bulb, phone, camera, plastic, neon, bright colors, anime, cartoon, text, watermark, bad anatomy, deformed, mutated."
        final_neg = f"{medieval_neg} {negative_prompt}"

        payload = {
            "prompt": prompt,
            "negative_prompt": final_neg,
            "steps": steps,
            "width": 512,
            "height": 512
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.api_url}/sdapi/v1/txt2img", json=payload)
                response.raise_for_status()
                data = response.json()
                return data["images"][0] # Returns base64
        except Exception as e:
            print(f"❌ SD Generation Error: {e}")
            return None

    async def kill(self):
        """Stops the SD container to free RAM."""
        print(f"💀 Stopping SD container: {self.container_name}")
        await self._run_command(f"docker stop {self.container_name}")

async def quick_generate(prompt: str) -> Optional[str]:
    """Helper to run the full cycle."""
    client = SDClient()
    if await client.spin_up():
        img = await client.generate(prompt)
        await client.kill()
        return img
    return None
