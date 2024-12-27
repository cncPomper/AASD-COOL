import logging

logging.getLogger().setLevel(logging.INFO)
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
from src.agents.traffic_light_controller.messages import TrafficLight
import networkx as nx
import json
from typing import Tuple, Union
import copy


class VehicleSimulator(Agent):
    def __init__(
        self,
        jid,
        password,
        graph: nx.Graph,
        start_node: str,
        finish_node: str,
        verify_security=False,
    ):
        super().__init__(jid, password, verify_security)
        self.start_node: str = start_node
        self.finish_node: str = finish_node
        self.vehicle_edge: Tuple[str, str] = None  # tuple of nodes
        self.graph: nx.G = graph
        self.plan: list[str] = ["A", "C", "D"]
        self.vehicle_speed_per_second = 3  # units per second
        self.vehicle_position_in_edge: float = 0

    class UpdateVehiclePosition(PeriodicBehaviour):
        """
        Periodic behaviour just for simulation.
        """

        def __init__(self, agent, period, start_at=None):
            super().__init__(period, start_at)
            self.agent = agent
            self.period_raw = period

        async def get_traffic_light_state(self, id: int) -> TrafficLight:
            msg = Message(to=f"traffic_light_controller_{id}@{SERVER_ADDRESS}")
            msg.set_metadata("msg_type", "get_traffic_light_request")
            await self.send(msg)
            msg = await self.receive(timeout=0.25)
            msg_body = json.loads(msg.body)
            return TrafficLight[msg_body["traffic_light"]]

        async def change_edge_available(self, node1, node2):
            traffic_light_id: Union[None, int] = self.agent.graph.get_edge_data(node1, node2)["traffic_light_id"]
            if traffic_light_id is None:
                return True
            curr_traffic_light: TrafficLight = await self.get_traffic_light_state(traffic_light_id)
            if curr_traffic_light != TrafficLight.RED:
                return True
            return False

        async def run(self):
            plan = copy.deepcopy(self.agent.plan)
            assert len(plan) > 2
            if not plan:
                return
            if self.agent.vehicle_edge is None:
                assert plan[0] == self.agent.start_node
                self.agent.vehicle_edge = (plan[0], plan[1])
            else:
                idx = plan.index(self.agent.vehicle_edge[0])
                plan = plan[idx:]

            edge_length = self.agent.graph.get_edge_data(plan[0], plan[1])["distance"]
            self.agent.vehicle_position_in_edge += self.period_raw * self.agent.vehicle_speed_per_second
            self.agent.vehicle_position_in_edge = min(edge_length, self.agent.vehicle_position_in_edge)
            logging.info(
                f"[VEHICLE SIMULATOR] Current progress on edge {self.agent.vehicle_edge}: {self.agent.vehicle_position_in_edge}/{edge_length}"
            )

            if self.agent.vehicle_position_in_edge >= edge_length:  # time to change edge
                if self.agent.finish_node == self.agent.vehicle_edge[1]:
                    logging.info(
                        f"[VEHICLE SIMULATOR] Reached finish node {self.agent.finish_node}. Stopping simulation."
                    )
                    await self.agent.stop()
                    return
                if await self.change_edge_available(plan[1], plan[2]):
                    logging.info(
                        f"[VEHICLE SIMULATOR] Changing edge from {self.agent.vehicle_edge} to {(plan[1], plan[2])}"
                    )
                    self.agent.vehicle_position_in_edge = 0
                    self.agent.vehicle_edge = plan[1], plan[2]
                else:
                    logging.info(
                        f"[VEHICLE SIMULATOR] Waiting for green light to change edge from {self.agent.vehicle_edge} to {(plan[1], plan[2])}"
                    )

    async def setup(self):
        b1 = self.UpdateVehiclePosition(self, period=0.1)

        self.add_behaviour(b1)
