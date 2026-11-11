import asyncio
import math

from lenia_client.indicator import IndicatorLight
from lenia_client.motion import MotionSensor
from lenia_client.person import CameraSensor


def steering_command(proximity_active, motion_active, proximity_strength=0.0, motion_strength=1.0,
                     motion_vector=(0.0, 0.0), screen_x='y', screen_y='x'):
    # Camera proximity retains radial escape priority throughout a perturbation.
    motion_active = motion_active and not proximity_active
    strength = max(proximity_strength if proximity_active else 0.0,
                   motion_strength if motion_active else 0.0)
    speed = round(1.0 + min(1.0, max(0.0, strength)), 2)
    if motion_active and math.hypot(*motion_vector) > 0:
        axes = dict(zip(('x', 'y'), motion_vector))
        mapped = tuple(axes[axis[-1]] * (-1 if axis.startswith('-') else 1) for axis in (screen_x, screen_y))
        length = math.hypot(*mapped)
        return {
            'action': 'movement',
            'direction': 'vector',
            'vector': dict(zip(('x', 'y'), (round(value / length, 2) for value in mapped))),
            'escape': True,
            'speed_multiplier': speed,
        }

    return {
        'action': 'movement',
        'direction': 'outward' if proximity_active or motion_active else 'inward',
        'speed_multiplier': speed,
    }


class SensorInputs:
    def __init__(self, device, person_proximity, motion_threshold, screen_x='y', screen_y='x', population=None):
        self.screen_x = screen_x
        self.screen_y = screen_y
        self.population = population if population is not None else {'fraction': 1.0}
        self.proximity = CameraSensor(person_proximity)
        try:
            self.motion = MotionSensor(device, motion_threshold)
            try:
                self.indicator = IndicatorLight()
            except BaseException:
                self.motion.close()
                raise
        except BaseException:
            self.proximity.close()
            raise

    def poll(self):
        self.proximity.poll()
        motion_active = self.motion.poll()
        self.indicator.update(self.population['fraction'])
        return steering_command(self.proximity.active, motion_active,
                                self.proximity.strength, self.motion.strength,
                                self.motion.vector, self.screen_x, self.screen_y)

    def close(self):
        try:
            self.indicator.close()
        finally:
            try:
                self.motion.close()
            finally:
                self.proximity.close()


async def monitor_sensors(commands, device='/dev/i2c-1', person_proximity=0.5, motion_threshold=0.12,
                          screen_x='y', screen_y='x', population=None):
    # Establish the idle mode immediately, including during startup calibration.
    previous = steering_command(False, False)
    commands.put_nowait(previous)
    opening = asyncio.create_task(asyncio.to_thread(SensorInputs, device, person_proximity, motion_threshold,
                                                   screen_x, screen_y, population))

    try:
        sensors = await asyncio.shield(opening)
    except asyncio.CancelledError:
        sensors = await opening
        await asyncio.to_thread(sensors.close)
        raise
    try:
        while True:
            reading = asyncio.create_task(asyncio.to_thread(sensors.poll))
            try:
                command = await asyncio.shield(reading)
            except asyncio.CancelledError:
                await reading
                raise
            if command != previous:
                commands.put_nowait(command)
                print(f'Sensor steering: {command}', flush=True)
                previous = command
            await asyncio.sleep(0.05)
    finally:
        await asyncio.to_thread(sensors.close)
