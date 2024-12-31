import logging

logging.getLogger().setLevel(logging.INFO)
from agents.traffic_light_controller.messages import TrafficLightProtocols
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
        jid,
        password,
        simulator: VehicleSimulator,
        verify_security=False,
    ):
        super().__init__(jid, password, verify_security)
        self.simulator = simulator

    class UpdateVehiclePosition(PeriodicBehaviour):
        """
        just for simulation of vehicle movement
        """

        async def run(self):
            result = await self.agent.simulator.step(self)
            if result == "STOP":
                await self.agent.stop()

    # Periodically sends a message to the navigation manager to request a route. 
    # When a response is received, it updates the vehicle's plan with the received route.
    class RequestRoute(PeriodicBehaviour):
        async def run(self):
            msg = Message(f"navigation_manager@{SERVER_ADDRESS}")
            msg.set_metadata("msg_type", "send_route")
            await self.send(msg)
            msg = await self.receive(timeout=1)
            if msg is not None:
                route: list[str] = json.loads(msg.body)["route"]
                logging.info(f"[VEHICLE NAVIGATOR] Received route: {route} from manager.")
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
        t2.set_metadata("msg_type", TrafficLightProtocols.SEND_TRAFFIC_LIGHT_ON_REQUEST)

        # This periodic behavior sends a message to the navigation manager to request a route. 
        # When a response is received, it updates the vehicle's navigation plan.
        b3 = self.RequestRoute(period=1)
        t3 = Template()
        t3.set_metadata("msg_type", "route_response")

        self.add_behaviour(b1)
        self.add_behaviour(b2, t2)
        self.add_behaviour(b3, t3)
