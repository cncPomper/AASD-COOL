import logging

logging.getLogger().setLevel(logging.INFO)
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
from .physical_traffic_light import PhysicalTrafficLight
from .messages import TrafficLight, TrafficLightProtocols
import datetime
import json


class TrafficLightControllerAgent(Agent):
    def __init__(
        self,
        jid,
        password,
        physical_traffic_light: PhysicalTrafficLight,
        verify_security=False,
    ):
        super().__init__(jid, password, verify_security)
        self.physical_traffic_light: PhysicalTrafficLight = physical_traffic_light
        self.traffic_light_last_changed: datetime.datetime = datetime.datetime.now()
        self.controlled_by_manager: bool = False  # whether current state is controlled by navigator manager
        self.CONTROLLED_BY_MANAGER_TIMEOUT = 10  # seconds

    #Periodically changes the traffic light state if not controlled by a manager. If controlled by a manager,
    # it checks if the timeout has been exceeded and reverts to auto control if necessary.
    class ChangeTrafficLight(PeriodicBehaviour):
        """
        Periodic behaviour just for simulation.
        """
        async def run(self):
            if not self.agent.controlled_by_manager:
                curr_light: TrafficLight = self.agent.physical_traffic_light.get_traffic_light()
                last_changed: datetime.datetime = self.agent.traffic_light_last_changed
                new_light: TrafficLight = self.agent.physical_traffic_light.simulator.iter(curr_light, last_changed)
                if new_light != curr_light:
                    self.agent.physical_traffic_light.set_traffic_light(new_light)
                    self.agent.traffic_light_last_changed = datetime.datetime.now()
                    logging.info(
                        f"[TRAFFIC_LIGHT {self.agent.physical_traffic_light.id}] Traffic light with ID {self.agent.physical_traffic_light.id} changed from {curr_light} to {new_light}"
                    )
            else:
                if datetime.datetime.now() - self.agent.traffic_light_last_changed > datetime.timedelta(
                    seconds=self.agent.CONTROLLED_BY_MANAGER_TIMEOUT
                ):
                    logging.info(
                        f"[TRAFFIC_LIGHT {self.agent.physical_traffic_light.id}] Traffic light with ID {self.agent.physical_traffic_light.id} exceeded timeout of controlled by manager. Going back to auto control."
                    )
                    self.agent.controlled_by_manager = False
                    self.agent.traffic_light_last_changed = datetime.datetime.now()

    #Periodically sends the current state of the traffic light to the navigation manager agent.
    class SendTrafficLightState(PeriodicBehaviour):
        async def run(self):
            msg = Message(to=f"navigation_manager@{SERVER_ADDRESS}")
            msg_body: str = json.dumps(
                {
                    "traffic_light": self.agent.physical_traffic_light.get_traffic_light().value,
                    "id": self.agent.physical_traffic_light.id,
                }
            )
            msg.body = msg_body
            msg.set_metadata("msg_type", TrafficLightProtocols.SEND_TRAFFIC_LIGHT.value)
            await self.send(msg)

    #Waits for a message to set the traffic light state. When a message is received, 
    # it updates the traffic light state and sets the controlled_by_manager flag to True.
    class SetTrafficLightState(OneShotBehaviour):
        """
        Expected message
        {
            "traffic_light": <RED/GREEN/...>
        }
        """
        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                logging.info(f"[TRAFFIC_LIGHT] Received request for setting traffic light state: {msg}")
                msg_json = json.loads(msg.body)
                new_traffic_light_state: TrafficLight = TrafficLight[msg_json["traffic_light"]]
                logging.info(
                    f"[TRAFFIC_LIGHT {self.agent.physical_traffic_light.id}] Traffic light with ID {self.agent.physical_traffic_light.id} is now controlled by manager. Current state: {new_traffic_light_state}"
                )
                self.agent.physical_traffic_light.set_traffic_light(new_traffic_light_state)
                self.agent.traffic_light_last_changed = datetime.datetime.now()
                self.agent.controlled_by_manager = True

    #Waits for a request message and sends the current traffic light state to the vehicle navigator agent.
    class SendTrafficLightStateOnRequest(OneShotBehaviour):
        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg = Message(to=f"vehicle_navigator@{SERVER_ADDRESS}")
                msg_body: str = json.dumps(
                    {
                        "traffic_light": self.agent.physical_traffic_light.get_traffic_light().value,
                    }
                )
                msg.body = msg_body
                msg.set_metadata("msg_type", TrafficLightProtocols.SEND_TRAFFIC_LIGHT_ON_REQUEST.value)
                await self.send(msg)

    async def setup(self):
        # We are not setting any metadata on this behaviour because
        #it runs periodically and does not depend on incoming messages
        b1 = self.ChangeTrafficLight(period=0.1)

        # This behaviour is associated with the message type "set_traffic_light"
        # it will handle messages that have message_type set to "set_traffic_light"
        t2 = Template()
        t2.set_metadata("msg_type", "set_traffic_light")
        b2 = self.SetTrafficLightState()

        # This behavior does not have any specific metadata because it runs periodically 
        # and sends the traffic light state to the navigation manager.
        b3 = self.SendTrafficLightState(period=1)

        # This behaviour is associated with the message type "get_traffic_light_request"
        t4 = Template()
        t4.set_metadata("msg_type", "get_traffic_light_request")
        b4 = self.SendTrafficLightStateOnRequest()

        self.add_behaviour(b1)
        self.add_behaviour(b2, t2)
        self.add_behaviour(b3)
        self.add_behaviour(b4, t4)
