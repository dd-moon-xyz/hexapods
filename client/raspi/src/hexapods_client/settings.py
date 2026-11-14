from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8',
        extra='ignore', allow_inf_nan=False,
    )

    hexapods_token: str = Field(default="", repr=False)
    server_url: str | None = None
    server_address: str = Field(default='192.168.0.15:9877', validation_alias='SERVER_ADDRESS')
    config: Path | None = Field(default=None, description='Path to a JSON preset; fetch the server preset when unset.')
    windowed: bool = Field(default=False, description='Display in an 800×800 window instead of fullscreen.')
    motion_device: str = Field(default='/dev/i2c-1', description='I2C device path for the motion sensor.')
    motion_threshold: float = Field(default=0.12, gt=0, description='Acceleration change in g required to detect motion.')
    motion_screen_x: Literal['x', '-x', 'y', '-y'] = 'y'
    motion_screen_y: Literal['x', '-x', 'y', '-y'] = 'x'
    person_proximity: float = Field(
        default=0.5, gt=0, lt=1,
        description='Person bounding-box height as a fraction of the image height required to detect proximity.',
    )

    @property
    def url(self) -> str:
        return self.server_url or f'ws://{self.server_address}/ws'

    @model_validator(mode='after')
    def validate_motion_axes(self):
        if self.motion_screen_x[-1] == self.motion_screen_y[-1]:
            raise ValueError('Screen X and Y must use different motion sensor axes')
        return self
