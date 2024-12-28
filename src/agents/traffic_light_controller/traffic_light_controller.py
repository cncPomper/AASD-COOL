import logging

logging.getLogger().setLevel(logging.INFO)
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
from .physical_traffic_light import PhysicalTrafficLight
from .messages import TrafficLight
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
            msg.set_metadata("msg_type", "send_traffic_light")
            await self.send(msg)

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
                msg_json = json.loads(msg.body)
                new_traffic_light_state: TrafficLight = TrafficLight[msg_json["traffic_light"]]
                logging.info(
                    f"[TRAFFIC_LIGHT {self.agent.physical_traffic_light.id}] Traffic light with ID {self.agent.physical_traffic_light.id} is now controlled by manager. Current state: {new_traffic_light_state}"
                )
                self.agent.physical_traffic_light.set_traffic_light(new_traffic_light_state)
                self.agent.traffic_light_last_changed = datetime.datetime.now()
                self.agent.controlled_by_manager = True

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
                msg.set_metadata("msg_type", "send_traffic_light_on_request")
                await self.send(msg)

    async def setup(self):
        b1 = self.ChangeTrafficLight(period=0.1)

        t2 = Template()
        t2.set_metadata("msg_type", "set_traffic_light")
        b2 = self.SetTrafficLightState()

        b3 = self.SendTrafficLightState(period=1)

        t4 = Template()
        t4.set_metadata("msg_type", "get_traffic_light_request")
        b4 = self.SendTrafficLightStateOnRequest()

        self.add_behaviour(b1)
        self.add_behaviour(b2, t2)
        self.add_behaviour(b3)
        self.add_behaviour(b4, t4)
