from enum import Enum

class TrafficLightProtocols(str, Enum):
    SEND_TRAFFIC_LIGHT = "send_traffic_light"
    SEND_TRAFFIC_LIGHT_ON_REQUEST = "send_traffic_light_on_request"

class TrafficLight(str, Enum):
    RED = "RED"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED_YELLOW = "RED_YELLOW"


class TrafficLightStateMsg:
    def __init__(self, traffic_light_id: int, traffic_light_state: TrafficLight):
        self.traffic_light_id = traffic_light_id
        self.traffic_light_state = traffic_light_state
