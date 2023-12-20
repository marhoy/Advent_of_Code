import re
from collections import defaultdict, deque

from pydantic import BaseModel


class Pulse(BaseModel):
    source: str
    dest: str
    type: bool

    def __repr__(self):
        type = "high" if self.type else "low"
        return f"{self.source} -{type}-> {self.dest}"

    def __str__(self) -> str:
        return self.__repr__()


class Module:
    name: str
    outputs: list[str]
    state: bool

    def process_pulse(self, pulse: Pulse):
        raise NotImplementedError


class FlipFlop(Module):
    def __init__(self, name: str, outputs: list[str], system: "System"):
        self.name = name
        self.outputs = outputs
        self.state = False
        self.system = system

    def process_pulse(self, pulse: Pulse):
        if not pulse.type:
            # We received a low pulse
            self.state = not self.state
            for output in self.outputs:
                self.system.queue_pulse(
                    Pulse(source=self.name, dest=output, type=self.state)
                )


class Conjuction(Module):
    def __init__(
        self, name: str, inputs: list[str], outputs: list[str], system: "System"
    ):
        self.name = name
        self.input_states = {input: False for input in inputs}
        self.outputs = outputs
        self.system = system

    @property
    def state(self):
        # If all inputs are high, the output is low
        return not all(self.input_states.values())

    def process_pulse(self, pulse: Pulse):
        self.input_states[pulse.source] = pulse.type
        for output in self.outputs:
            self.system.queue_pulse(
                Pulse(
                    source=self.name,
                    dest=output,
                    type=self.state,
                )
            )


class BroadCaster(Module):
    def __init__(self, name: str, outputs: list[str], system: "System"):
        self.name = name
        self.outputs = outputs
        self.system = system

    def process_pulse(self, pulse: Pulse):
        for output in self.outputs:
            self.system.queue_pulse(
                Pulse(source=self.name, dest=output, type=pulse.type)
            )


class System:
    def __init__(self):
        self.modules = dict()
        self.high_pulses = 0
        self.low_pulses = 0
        self.button_pushes = 0
        self.queue = deque()
        self.cycle_times = None

    def add_module(self, module: Module):
        self.modules[module.name] = module

    def queue_pulse(self, pulse: Pulse):
        # print(pulse)
        self.queue.append(pulse)

    def process_queue(self):
        while self.queue:
            self.find_cycle_times()  # For Part 2
            pulse = self.queue.popleft()
            if pulse.type:
                self.high_pulses += 1
            else:
                self.low_pulses += 1
            if pulse.dest in self.modules:
                self.modules[pulse.dest].process_pulse(pulse)

    def push_button(self):
        start_pulse = Pulse(source="button", dest="broadcaster", type=False)
        self.button_pushes += 1
        self.queue_pulse(start_pulse)
        self.process_queue()
        return self.high_pulses * self.low_pulses

    def find_cycle_times(self):
        """For Part 2, we need to find the cycle times for the inputs to &zg."""
        input_names = self.modules["zg"].input_states.keys()
        if self.cycle_times is None:
            self.cycle_times = {module: 0 for module in input_names}
        for module in input_names:
            if (
                self.modules[module].state
                and self.cycle_times[module] == 0
                and self.button_pushes > 1
            ):
                self.cycle_times[module] = self.button_pushes


def parse_input(filename: str) -> System:
    inputs: defaultdict[str, list[str]] = defaultdict(list[str])
    outputs = dict()
    system = System()

    with open(filename) as file:
        for line in file:
            if match := re.match(r"([%&]?)(\w+) -> (.*)", line.strip()):
                output_names = match.group(3).split(", ")
                outputs[match.group(1) + match.group(2)] = output_names
                for output in output_names:
                    inputs[output].append(match.group(2))

    for name, output_names in outputs.items():
        if name.startswith("%"):
            system.add_module(
                FlipFlop(name=name[1:], outputs=output_names, system=system)
            )
        elif name.startswith("&"):
            system.add_module(
                Conjuction(
                    name=name[1:],
                    inputs=inputs[name[1:]],
                    outputs=output_names,
                    system=system,
                )
            )
        else:
            system.add_module(
                BroadCaster(name=name, outputs=output_names, system=system)
            )

    return system
