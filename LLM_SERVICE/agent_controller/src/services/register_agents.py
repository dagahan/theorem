from src.agents.enbi import EnbiAgent


class RegisterAgents:
    def __init__(self) -> None:
        pass


    def register_agents(self) -> None:
        # here we need to register every agent.
        # it's register all of agents once on service start.
        EnbiAgent().register()


