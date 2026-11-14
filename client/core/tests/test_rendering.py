import os
import unittest
from unittest.mock import patch

import pygame

from client_core.rendering import Viewer


class RenderingTests(unittest.TestCase):
    def test_fallback_preserves_live_window_size(self):
        with patch.dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_RENDER_DRIVER="software"):
            pygame.display.init()
            viewer = Viewer()
            try:
                self.assertEqual(viewer.output_size, (1024, 1024))
                viewer.draw(pygame.Surface((256, 256)))
                viewer.draw(pygame.Surface((1024, 1024)), resize_window=False)
                self.assertEqual(viewer.output_size, (256, 256))
                viewer.draw(pygame.Surface((512, 512)))
                self.assertEqual(viewer.output_size, (512, 512))
            finally:
                viewer.close()
                pygame.display.quit()

    def test_native_pixels_and_nearest_sampling_preserve_checkerboard(self):
        with patch.dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_RENDER_DRIVER="software"):
            pygame.display.init()
            viewer = Viewer()
            try:
                pixels = bytes(
                    value
                    for y in range(64)
                    for x in range(64)
                    for value in ((255,) * 3 if (x + y) % 2 else (0,) * 3)
                )

                frame = pygame.image.frombytes(pixels, (64, 64), "RGB")
                viewer.draw(frame)
                rendered = viewer.renderer.to_surface()
                self.assertEqual(rendered.get_size(), (64, 64))
                self.assertEqual(pygame.image.tobytes(rendered, "RGB"), pixels)
                viewer.window.size = (128, 128)
                pygame.event.pump()
                viewer.draw(frame)
                enlarged = viewer.renderer.to_surface()
                expected = pygame.transform.scale(frame, (128, 128))
                self.assertEqual(enlarged.get_size(), (128, 128))
                self.assertEqual(
                    pygame.image.tobytes(enlarged, "RGB"),
                    pygame.image.tobytes(expected, "RGB"),
                )

            finally:
                viewer.close()
                pygame.display.quit()
