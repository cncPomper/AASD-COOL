import logging

logging.getLogger().setLevel(logging.INFO)
from spade.message import Message
from ...config import SERVER_ADDRESS
from src.agents.traffic_light_controller.messages import TrafficLight
import networkx as nx
import json
from typing import Tuple, Union
import copy


class VehicleSimulator:
    def __init__(
        self,
        graph: nx.Graph,
        start_node: str,
        finish_node: str,
    ):
        self.start_node: str = start_node
        self.finish_node: str = finish_node
        self.vehicle_edge: Tuple[str, str] = None  # tuple of nodes
        self.graph: nx.G = graph
        self.plan: Union[None, list[str]] = None
        self.vehicle_speed_per_second = 3  # units per second
        self.vehicle_position_in_edge: float = 0

    async def get_traffic_light_state(self, behav, id: int) -> Union[TrafficLight]:
        msg = Message(to=f"traffic_light_controller_{id}@{SERVER_ADDRESS}")
        msg.set_metadata("msg_type", "get_traffic_light_request")
        await behav.send(msg)
        msg = await behav.receive(timeout=0.25)
        if msg is None:
            return None
        msg_body = json.loads(msg.body)
        print(msg_body)
        return TrafficLight[msg_body["traffic_light"]]

    async def check_green_light(self, node1, node2, behav):
        traffic_light_id: Union[None, int] = self.graph.get_edge_data(node1, node2)["traffic_light_id"]
        if traffic_light_id is None:
            return True
        curr_traffic_light: Union[None, TrafficLight] = await self.get_traffic_light_state(behav, traffic_light_id)
        if curr_traffic_light != TrafficLight.RED and curr_traffic_light is not None:
            return True
        return False

    async def step(self, behav):
        plan = copy.deepcopy(self.plan)
        if not plan:
            return
        assert len(plan) > 2
        if self.vehicle_edge is None:
            assert plan[0] == self.start_node
            self.vehicle_edge = (plan[0], plan[1])
        else:
            idx = plan.index(self.vehicle_edge[0])
            plan = plan[idx:]

        edge_length = self.graph.get_edge_data(plan[0], plan[1])["distance"]
        self.vehicle_position_in_edge += behav.period.total_seconds() * self.vehicle_speed_per_second
        self.vehicle_position_in_edge = min(edge_length, self.vehicle_position_in_edge)
        logging.info(
            f"[VEHICLE SIMULATOR] Current progress on edge {self.vehicle_edge}: {self.vehicle_position_in_edge}/{edge_length}"
        )

        if self.vehicle_position_in_edge >= edge_length:  # time to change edge
            if self.finish_node == self.vehicle_edge[1]:
                logging.info(f"[VEHICLE SIMULATOR] Reached finish node {self.finish_node}. Stopping simulation.")
                return "STOP"
            if await self.check_green_light(plan[1], plan[2], behav):  # wait for green light
                logging.info(f"[VEHICLE SIMULATOR] Changing edge from {self.vehicle_edge} to {(plan[1], plan[2])}")
                self.vehicle_position_in_edge = 0
                self.vehicle_edge = plan[1], plan[2]
            else:
                logging.info(
                    f"[VEHICLE SIMULATOR] Waiting for green light to change edge from {self.vehicle_edge} to {(plan[1], plan[2])}"
                )
