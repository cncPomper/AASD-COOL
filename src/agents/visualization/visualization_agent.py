import logging
from typing import Tuple

logging.getLogger().setLevel(logging.INFO)
from src.agents.traffic_light_controller.messages import TrafficLightProtocols
import json
import networkx as nx
import matplotlib.pyplot as plt
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from spade.template import Template
import threading

class VehiclePosition:
    def __init__(self, current_edge: Tuple[str, str], position_on_edge: float):
        self.current_edge = current_edge
        self.position_on_edge = position_on_edge
        self.pos = nx.spring_layout(self.graph)
        self.fig, self.ax = plt.subplots()
        plt.ion()

class VisualizerAgent(Agent):
    def __init__(self, jid, password, graph, verify_security=False):
        super().__init__(jid, password, verify_security)
        self.graph = graph
        self.vehicle_positions = {}

    class UpdateVisualization(OneShotBehaviour):
        async def run(self):
            while 1:
                msg = await self.receive(timeout=1)
                if not msg:
                    continue
                logging.info(f"[VISUALIZER] Received message: {msg}")
                msg_json = json.loads(msg.body)
                vehicle_id = msg_json["vehicle_id"]
                current_edge = msg_json.get("current_edge")
                position_on_edge = msg_json["position_on_edge"]
                if current_edge is not None and position_on_edge is not None:
                    logging.info(f"[VISUALIZER] Received position update for vehicle {vehicle_id} at edge {current_edge} at position {position_on_edge}")
                    current_edge = tuple(current_edge)  # Convert to tuple
                    position_on_edge = position_on_edge
                    self.agent.vehicle_positions[vehicle_id] = VehiclePosition(current_edge, position_on_edge)
                    self.agent.update_visualization()

    def update_visualization(self):
        self.ax.clear()
        nx.draw(self.graph, self.pos, ax=self.ax, with_labels=True, node_size=500, node_color="lightblue", font_size=10, font_weight="bold")
        
        # Draw vehicles
        for vehicle_id, vehicle_position in self.vehicle_positions.items():
            node1, node2 = vehicle_position.current_edge
            x1, y1 = self.pos[node1]
            x2, y2 = self.pos[node2]
            x = x1 + vehicle_position.position_on_edge * (x2 - x1)
            y = y1 + vehicle_position.position_on_edge * (y2 - y1)
            logging.info(f"[VISUALIZER] Drawing vehicle {vehicle_id} at position ({x}, {y})")
            self.ax.plot(x, y, 'ro')  # Draw vehicle as a red dot
            self.ax.text(x, y, f'{vehicle_id}', fontsize=12, ha='right')

        plt.draw()
        plt.pause(1)  # Update every second

    async def setup(self):
        b1 = self.UpdateVisualization()
        t1 = Template()
        t1.set_metadata("msg_type", "vehicle_position_update_response")
        self.add_behaviour(b1, t1)