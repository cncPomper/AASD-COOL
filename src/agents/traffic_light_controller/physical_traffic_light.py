import datetime
from .messages import TrafficLight
import datetime


class TrafficLightSimulator:
    def __init__(self, red_time: float, yellow_time, green_time: float, red_yellow_time: float):
        """
        All times in seconds
        """
        self.red_time: float = red_time
        self.yellow_time: float = yellow_time
        self.green_time: float = green_time
        self.red_yellow_time: float = red_yellow_time

    def iter(self, curr_traffic_light: TrafficLight, last_changed: datetime.datetime) -> TrafficLight:
        """
        Returns new traffic light
        """
        if curr_traffic_light == TrafficLight.RED:
            if datetime.datetime.now() - last_changed >= datetime.timedelta(seconds=self.red_time):
                return TrafficLight.RED_YELLOW
            return TrafficLight.RED

        if curr_traffic_light == TrafficLight.RED_YELLOW:
            if datetime.datetime.now() - last_changed >= datetime.timedelta(seconds=self.red_yellow_time):
                return TrafficLight.GREEN
            return TrafficLight.RED_YELLOW

        if curr_traffic_light == TrafficLight.GREEN:
            if datetime.datetime.now() - last_changed >= datetime.timedelta(seconds=self.green_time):
                return TrafficLight.YELLOW
            return TrafficLight.GREEN

        if curr_traffic_light == TrafficLight.YELLOW:
            if datetime.datetime.now() - last_changed >= datetime.timedelta(seconds=self.yellow_time):
                return TrafficLight.RED
            return TrafficLight.YELLOW

        raise ValueError(f"Unknown traffic light state: {curr_traffic_light}")


class PhysicalTrafficLight:
    """
    Class representing physical traffic light
    """

    def __init__(
        self,
        id: int,
        simulator: TrafficLightSimulator,
        default_light: TrafficLight = TrafficLight.RED,
    ):
        self.id: int = id
        self.simulator = simulator
        self.traffic_light_state: TrafficLight = default_light

    def set_traffic_light(self, state: TrafficLight):
        self.traffic_light_state = state

    def get_traffic_light(self) -> TrafficLight:
        return self.traffic_light_state
