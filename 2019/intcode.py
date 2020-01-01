import collections
from typing import Tuple, List, Optional, Iterable
import logging

# Configure logging
logging.basicConfig(format='[%(levelname)s] %(name)s(%(lineno)s): %(message)s',
                    level=logging.WARNING)
LOG = logging.getLogger(__name__)

"""
This is used on several days:
https://adventofcode.com/2019/day/2
https://adventofcode.com/2019/day/5
https://adventofcode.com/2019/day/7
https://adventofcode.com/2019/day/9
https://adventofcode.com/2019/day/11
https://adventofcode.com/2019/day/13
"""


class Machine:
    def __init__(self,
                 program: str,
                 phase: int = None,
                 machine_id: Optional[int] = 0,
                 loglevel: int = logging.INFO
                 ) -> None:
        self._memory = self.str2mem(program)
        self.ptr = 0
        self.relative_base = 0
        if phase is not None:
            self.phase = [phase]
        else:
            self.phase = []
        self._inputs = collections.deque()
        self._outputs = collections.deque()
        self.finished = False
        self.machine_id = machine_id
        LOG.setLevel(loglevel)

    # Internal details: For both the input and output queue, we add new values
    # to the end and remove values from the head (left). Thus, the elements
    # were added in order from left to right.

    @staticmethod
    def str2mem(line: str) -> List[int]:
        """Convert a program string to a list of ints"""
        return [int(i) for i in line.split(",")]

    @staticmethod
    def get_opcode_and_modes(number: int) -> Tuple[int, List[int]]:
        """Convert an int into an opcode and 3 parameter modes"""
        s = "{:05d}".format(number)
        opcode = int(s[-2:])
        modes = list(map(int, s[:3]))
        modes.reverse()
        for mode in modes:
            if mode not in [0, 1, 2]:
                raise ValueError("Illegal mode: {}".format(mode))
        return opcode, modes

    def extend_memory(self, max_address):
        """Allocate more memory such that max_address is valid"""
        extra_size = max_address + 1 - len(self._memory)
        LOG.debug("Allocating extra memory: {}".format(extra_size))
        self._memory.extend([0] * extra_size)

    def get_mem_value(self, address):
        """Get the value at an address"""
        if address >= len(self._memory):
            self.extend_memory(address)
        return self._memory[address]

    def set_mem_value(self, address, value):
        """Set the value at an address to a value"""
        if address >= len(self._memory):
            self.extend_memory(address)
        LOG.debug("Writing to address {}: {}".format(address, value))
        self._memory[address] = value

    def _get_params(self, modes: List[int], ptypes: str) -> List[int]:
        """Read parameters from memory"""
        values = []
        params = self._memory[self.ptr + 1: self.ptr + len(modes) + 1]
        for param, mode, ptype in zip(params, modes, ptypes):
            # Relative mode
            if mode == 2:
                param += self.relative_base

            # If reading in position or relative mode, look up the value at
            # that address. Otherwise return the parameter directly
            if ptype == 'r' and mode in [0, 2]:
                param = self.get_mem_value(param)
            values.append(param)

        return values

    def add_input(self, value: int) -> None:
        """Add a value to the input queue"""
        self._inputs.append(value)

    def add_inputs(self, values: Iterable[int]) -> None:
        """Add input values from an iterable"""
        for value in values:
            self._inputs.append(value)

    def get_output(self) -> int:
        """Get value from the output queue"""
        return self._outputs.popleft()

    def get_outputs(self, n: int = None) -> Tuple[int]:
        """Get several (n) values from the output queue
        If n is not specified, all outputs are returned"""
        if n is None:
            n = len(self._outputs)
        assert len(self._outputs) >= n
        return tuple([self.get_output() for _ in range(n)])

    @property
    def has_output(self) -> bool:
        """Returns true if the output queue is non-empty"""
        return bool(self._outputs)

    def run(self) -> None:
        """Run the machine until it halts or waits for input"""
        while True:
            opcode_value = self.get_mem_value(self.ptr)
            opcode, modes = self.get_opcode_and_modes(opcode_value)
            if opcode == 1:
                p1, p2, p3 = self._get_params(modes, 'rrw')
                self.set_mem_value(p3, p1 + p2)
                self.ptr += 4
            elif opcode == 2:
                p1, p2, p3 = self._get_params(modes, 'rrw')
                self.set_mem_value(p3, p1 * p2)
                self.ptr += 4
            elif opcode == 3:
                p1, *_ = self._get_params(modes, 'w')
                if self.phase:  # This will only be True the first time
                    self.set_mem_value(p1, self.phase.pop())
                elif not self._inputs:
                    LOG.info("Machine {}: Waiting for new input".format(
                        self.machine_id))
                    break
                else:
                    input_value = self._inputs.popleft()
                    LOG.debug("Machine {}: Popping input {}".format(
                        self.machine_id, input_value))
                    self.set_mem_value(p1, input_value)
                self.ptr += 2
            elif opcode == 4:
                output, *_ = self._get_params(modes, 'r')
                LOG.debug("Machine {}: outputting: {}".format(
                    self.machine_id, output))
                self._outputs.append(output)
                self.ptr += 2
            elif opcode == 5:
                p1, p2 = self._get_params(modes, 'rr')
                if p1:
                    self.ptr = p2
                else:
                    self.ptr += 3
            elif opcode == 6:
                p1, p2 = self._get_params(modes, 'rr')
                if not p1:
                    self.ptr = p2
                else:
                    self.ptr += 3
            elif opcode == 7:
                p1, p2, p3 = self._get_params(modes, 'rrw')
                self.set_mem_value(p3, int(p1 < p2))
                self.ptr += 4
            elif opcode == 8:
                p1, p2, p3 = self._get_params(modes, 'rrw')
                self.set_mem_value(p3, int(p1 == p2))
                self.ptr += 4
            elif opcode == 9:
                p1, *_ = self._get_params(modes, 'r')
                self.relative_base += p1
                self.ptr += 2
            elif opcode == 99:
                self.finished = True
                LOG.info("Machine {} is halted".format(self.machine_id))
                break
            else:
                raise ValueError("Unknown opcode: {}".format(opcode))
