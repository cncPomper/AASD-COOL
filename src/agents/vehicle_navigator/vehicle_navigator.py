import logging

logging.getLogger().setLevel(logging.INFO)
from src.agents.traffic_light_controller.messages import TrafficLightProtocols
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
from spade.template import Template
from ...config import SERVER_ADDRESS
from .vehicle_simulator import VehicleSimulator
import json


class VehicleNavigator(Agent):
    def __init__(
        self,
        jid: str,
        password: str,
        simulator: VehicleSimulator,
        target_node: str,
        vehicle_id: int,
        verify_security: bool = False,
        isEmergency: bool = False,
    ):
        super().__init__(jid, password, verify_security)
        self.simulator = simulator
        self.target_node = target_node
        self.vehicle_id = vehicle_id
        self.isEmergency = isEmergency

    class UpdateVehiclePosition(PeriodicBehaviour):
        """
            Simulation of the movement and provide info to VisualizationAgent

        """
        async def run(self):
            vehicle_edge, vehicle_position_in_edge, status = await self.agent.simulator.step(self)
            logging.info(f"[VEHICLE NAVIGATOR] Vehicle {self.agent.vehicle_id} is at edge {vehicle_edge} at position {vehicle_position_in_edge} - status: {status}")
            if status == "STOP":
                await self.agent.stop()

            if vehicle_edge is not None and vehicle_position_in_edge is not None:
                # Send position update to the visualiation agent
                logging.info(f"[VEHICLE NAVIGATOR] Sending position update to visualization agent.")
                position_update_msg = Message(to=f"visualizer@{SERVER_ADDRESS}")
                position_update_msg.set_metadata("msg_type", "vehicle_position_update_response")
                position_update_msg.body = json.dumps({
                    "vehicle_id": self.agent.vehicle_id,
                    "current_edge": vehicle_edge,
                    "position_on_edge": vehicle_position_in_edge
                })
                await self.send(position_update_msg)

    # Periodically sends a message to the navigation manager to request a route.
    # When a response is received, it updates the vehicle's plan with the received route.
    class RequestRoute(PeriodicBehaviour):
        async def run(self):
            msg = Message(f"navigation_manager@{SERVER_ADDRESS}")
            msg_body = {
                "target": self.agent.target_node,
                "vehicle_id": self.agent.vehicle_id,
                "isEmergency": self.agent.isEmergency,
            }
            msg.body = json.dumps(msg_body)
            msg.set_metadata("msg_type", "send_route")
            await self.send(msg)
            msg = await self.receive(timeout=1)
            if msg is not None:
                route: list[str] = json.loads(msg.body)["route"]
                vehicleType = " Emergency" if self.agent.isEmergency else " Normal"
                logging.info(f"[VEHICLE NAVIGATOR{vehicleType}] Received route: {route} from manager.")
                self.agent.simulator.plan = route

    # Periodically sends the current vehicle position
    # to the navigation manager if the vehicle is on an edge.
    class SendPosition(PeriodicBehaviour):
        async def run(self):
            if self.agent.simulator.vehicle_edge is not None:
                msg = Message(f"navigation_manager@{SERVER_ADDRESS}")
                msg_body = {
                    "node1": self.agent.simulator.vehicle_edge[0],
                    "node2": self.agent.simulator.vehicle_edge[1],
                    "vehicle_id": self.agent.vehicle_id,
                    "isEmergency": self.agent.isEmergency,
                }
                msg.body = json.dumps(msg_body)
                msg.set_metadata("msg_type", "send_vehicle_position")
                await self.send(msg)

    async def setup(self):
        # add behaviour - Sends the vehicle's position periodically.
        b1 = self.SendPosition(period=1)

        # add behaviour - Updates the vehicle's position periodically
        # being associated with send traffic light on request message.
        b2 = self.UpdateVehiclePosition(period=0.1)
        t2 = Template()
        t2.set_metadata("msg_type", TrafficLightProtocols.SEND_TRAFFIC_LIGHT_ON_REQUEST.value)

        # This periodic behavior sends a message to the navigation manager to request a route.
        # When a response is received, it updates the vehicle's navigation plan.
        b3 = self.RequestRoute(period=1)
        t3 = Template()
        t3.set_metadata("msg_type", "route_response")

        self.add_behaviour(b1)
        self.add_behaviour(b2, t2)
        self.add_behaviour(b3, t3)
