import asyncio
import logging

logging.getLogger().setLevel(logging.INFO)
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
import json
from src.agents.traffic_light_controller.messages import TrafficLight


class NavigatorManagerAgent(Agent):
    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security)

    class SetTrafficLightState(OneShotBehaviour):
        def __init__(self, agent):
            super().__init__()
            self.agent = agent

        async def run(self):
            await asyncio.sleep(15)
            id: int = 1
            msg = Message(to=f"traffic_light_controller_{id}@{SERVER_ADDRESS}")
            msg.set_metadata("msg_type", "set_traffic_light")
            msg_body: str = json.dumps({"traffic_light": TrafficLight.GREEN.value})
            msg.body = msg_body
            logging.info(f"Manager changing traffic light state for ID {id}")
            await self.send(msg)

    class AwaitTrafficLightState(OneShotBehaviour):
        """
        Expected message
        {
            "traffic_light": <RED/GREEN/...>
            "id": <traffic_light_id>
        }
        """

        def __init__(self, agent):
            super().__init__()
            self.agent = agent

        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                id: int = msg_json["id"]
                traffic_light: TrafficLight = TrafficLight[msg_json["traffic_light"]]
                logging.info(f"Navigation manager received state {traffic_light} from ID {id}")

    async def setup(self):
        b1 = self.AwaitTrafficLightState(self)
        t1 = Template()
        t1.set_metadata("msg_type", "send_traffic_light")

        b2 = self.SetTrafficLightState(self)

        self.add_behaviour(b1, t1)
        self.add_behaviour(b2)
