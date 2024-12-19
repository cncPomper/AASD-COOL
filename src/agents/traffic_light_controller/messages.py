from enum import Enum


class TrafficLight(Enum):
    RED = "RED"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED_YELLOW = "RED_YELLOW"


class TrafficLightStateMsg:
    def __init__(self, traffic_light_id: int, traffic_light_state: TrafficLight):
        self.traffic_light_id = traffic_light_id
        self.traffic_light_state = traffic_light_state
