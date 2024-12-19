import spade
from src.agents.traffic_light_controller.traffic_light_controller import TrafficLightControllerAgent
from src.agents.traffic_light_controller.physical_traffic_light import TrafficLightSimulator, PhysicalTrafficLight
from src.agents.navigation_manager.navigation_manager import NavigatorManagerAgent

from src.config import SERVER_ADDRESS


async def main():
    # traffic light agent setup
    simulator = TrafficLightSimulator(5, 1, 5, 2)
    physical_traffic_light = PhysicalTrafficLight(1, simulator)
    agent = TrafficLightControllerAgent(f"traffic_light_controller_1@{SERVER_ADDRESS}", "admin", physical_traffic_light)
    await agent.start(auto_register=True)
    
    manager_agent = NavigatorManagerAgent(f"navigation_manager@{SERVER_ADDRESS}", 'admin')
    await manager_agent.start(auto_register=True)

    await spade.wait_until_finished(manager_agent)


if __name__ == "__main__":
    spade.run(main())
