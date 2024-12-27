import json
import networkx
from src.agents.traffic_light_controller.physical_traffic_light import (
    PhysicalTrafficLight,
    TrafficLightSimulator,
    TrafficLight,
)
from typing import Dict


def load_graph(path: str) -> networkx.Graph:
    with open(path, "rb") as file:
        data = json.load(file)
    g = networkx.Graph()
    for node in data["nodes"]:
        g.add_node(node)
    for edge in data["edges"]:
        g.add_edge(edge["node1"], edge["node2"], traffic_light_id=edge["traffic_light_id"], distance=edge["distance"])
    g.start_node = data["start_node"]
    g.finish_node = data["finish_node"]
    return g


def load_lights(path: str) -> Dict[int, PhysicalTrafficLight]:
    """
    returns mapping id -> physical traffic light object
    """
    with open(path, "rb") as file:
        data = json.load(file)
    lights: dict[int, PhysicalTrafficLight] = {}
    for light in data["lights"]:
        id = light["id"]
        simulator = TrafficLightSimulator(
            red_time=light["red_time"],
            yellow_time=light["yellow_time"],
            green_time=light["green_time"],
            red_yellow_time=light["red_yellow_time"],
        )
        physical_traffic_light = PhysicalTrafficLight(id, simulator, default_light=TrafficLight[light["default"]])
        lights[id] = physical_traffic_light
    return lights
