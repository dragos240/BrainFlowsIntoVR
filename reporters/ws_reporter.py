import asyncio
from threading import Thread
from time import sleep
from typing import Dict, List, Optional, Tuple
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.server import WebSocketServerProtocol, serve

from reporters.base_reporter import Base_Reporter

DEFAULT_WS_HOST = "localhost"
DEFAULT_PORT = 12345

PairType = Tuple[str, float]


class WS_Reporter_Worker(Thread):
    def __init__(self, *args, **kwargs):
        for arg in kwargs["args"]:
            if isinstance(arg, WS_Reporter):
                self.reporter = arg
        super().__init__(*args,
                         **kwargs,
                         name="WS_Reporter")

    def start(self):
        while True:
            if self.reporter.started:
                break
            sleep(0.1)
        return super().start()


class WS_Reporter(Base_Reporter):
    """Websocket Reporter for Resonite"""

    thread = Optional[WS_Reporter_Worker]

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.messages_to_be_sent: asyncio.Queue[PairType] = asyncio.Queue()
        self.thread = None
        self.started = False

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
        # We have to start a new thread to run asyncio.run so it doesn't
        # block the main program
        if self.thread is None:
            self.thread = WS_Reporter_Worker(target=self.run, args=[self])
            self.thread.start()
        send_pairs = self.flatten(data_dict)

        for pair in send_pairs:
            self.messages_to_be_sent.put_nowait(pair)

        return send_pairs
