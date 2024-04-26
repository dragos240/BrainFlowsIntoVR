import asyncio
from typing import Dict, List, Tuple
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.server import WebSocketServerProtocol, serve

from reporters.base_reporter import Base_Reporter

DEFAULT_WS_HOST = "localhost"
DEFAULT_PORT = 12345

PairType = Tuple[str, float]


class WS_Reporter(Base_Reporter):
    """Websocket Reporter for Resonite"""

    messages_to_be_sent: asyncio.Queue[PairType]

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.messages_to_be_sent = asyncio.Queue()

    def flatten(self, data_dict: Dict) -> List[PairType]:
        """Flatten k:v pairs into a List of Tuples with format (name, value)

        Args:
            data_dict (Dict): The source values

        Returns:
            List[PairType]: The List of pairs
        """
        pairs = []
        for param_name, param_value in data_dict.items():
            if not isinstance(param_value, float):
                # To make it easier for the Protoflux, only accept float based
                # blendshapes
                continue
            pairs.append((param_name, param_value))

        return pairs

    async def server_handler(self, websocket: WebSocketServerProtocol):
        """The websocket server handler

        This will continuously try to get Pairs as they become available
        and will send them off to the connected Resonite client in the format
        BLENDSHAPE VALUE

        Args:
            websocket (WebSocketServerProtocol): The websocket to send to
        """
        while True:
            try:
                blendshape, value = await self.messages_to_be_sent.get()
                await websocket.send(f"{blendshape} {value}")
            except (ConnectionClosedOK, ConnectionClosedError):
                break

    async def start(self):
        """Start the websocket server"""
        # Resonite does not run a websocket server, rather it connects to
        # an existing websocket server, so we need a server, not a client
        async with serve(self.server_handler, self.host, self.port):
            await asyncio.Future()

    def run(self):
        asyncio.run(self.start())

    def send(self, data_dict: Dict):
        send_pairs = self.flatten(data_dict)

        for pair in send_pairs:
            self.messages_to_be_sent.put_nowait(pair)

        return send_pairs
