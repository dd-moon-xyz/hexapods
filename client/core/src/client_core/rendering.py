import pygame
from pygame._sdl2 import Renderer, Texture


class Viewer:
    def __init__(self, fullscreen: bool = False, fit_display: bool = False):
        self.window = pygame.Window(
            "Hexapod stream — connecting…", size=(800, 800) if fit_display else (1024, 1024), allow_high_dpi=True
        )

        if fullscreen:
            self.window.set_fullscreen(desktop=True)

        self.fit_display = fit_display
        self.renderer = Renderer(self.window, vsync=False)
        self.texture = None
        self.frame_size = None

    @property
    def output_size(self):
        return self.renderer.get_viewport().size

    def resize(self, size: tuple[int, int]) -> None:
        if self.fit_display:
            return

        drawable = self.renderer.get_viewport().size
        self.window.size = tuple(
            max(1, round(pixels * logical / physical))
            for pixels, logical, physical in zip(size, self.window.size, drawable)
        )

        self.window.title = "Hexapod stream — Hold Space/C outward, V inward, Esc to quit"

    def draw(self, frame: pygame.Surface, resize_window: bool = True) -> None:
        size = frame.get_size()
        if self.frame_size != size:
            if resize_window:
                self.resize(size)

            self.texture = Texture(self.renderer, size, streaming=True, scale_quality=0)
            self.texture.blend_mode = pygame.BLENDMODE_NONE
            self.frame_size = size

        self.texture.update(frame)
        destination = None
        if self.fit_display:
            width, height = self.output_size
            scale = min(width / size[0], height / size[1])
            destination = pygame.Rect(0, 0, round(size[0] * scale), round(size[1] * scale))
            destination.center = (width // 2, height // 2)
            self.renderer.draw_color = (0, 0, 0, 255)
            self.renderer.clear()

        self.texture.draw(dstrect=destination)
        self.renderer.present()

    def close(self) -> None:
        self.texture = None
        self.renderer = None
        self.window.destroy()
