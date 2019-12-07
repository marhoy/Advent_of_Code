import collections
from typing import Tuple, List, Optional
import logging

# Configure logging
logging.basicConfig(format='[%(levelname)s] %(name)s(%(lineno)s): %(message)s',
                    level=logging.WARNING)
LOG = logging.getLogger(__name__)


class Machine:
    def __init__(self,
                 program: str,
                 phase: int,
                 machine_id: Optional[int] = None,
                 loglevel: int = logging.WARNING
                 ) -> None:
        self.memory = self.str2mem(program)
        self.ptr = 0
        self.phase = [phase]
        self.inputs = collections.deque()
        self.outputs = collections.deque()
        self.finished = False
        self.machine_id = machine_id
        LOG.setLevel(loglevel)

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
        if modes[2] == 1:
            raise ValueError("Mode of parameter 3 cannot not be 1")
        return opcode, modes

    def get_params(self,
                   modes: List[int],
                   ptypes: str
                   ) -> List[int]:
        """Read parameters from memory"""
        values = []
        params = self.memory[self.ptr + 1: self.ptr + len(modes) + 1]
        for param, mode, ptype in zip(params, modes, ptypes):
            if mode == 1 or ptype == 'w':
                values.append(param)
            elif mode == 0:
                values.append(self.memory[param])
        return values

    def add_input(self, value: int) -> None:
        """Add a value to the input queue"""
        self.inputs.appendleft(value)

    def run(self) -> None:
        """Run the machine until it halts or waits for input"""
        while True:
            opcode, modes = self.get_opcode_and_modes(self.memory[self.ptr])
            if opcode == 1:
                p1, p2, p3 = self.get_params(modes, 'rrw')
                self.memory[p3] = p1 + p2
                self.ptr += 4
            elif opcode == 2:
                p1, p2, p3 = self.get_params(modes, 'rrw')
                self.memory[p3] = p1 * p2
                self.ptr += 4
            elif opcode == 3:
                p1, *_ = self.get_params(modes, 'w')
                if self.phase:  # This will only be True the first time
                    self.memory[p1] = self.phase.pop()
                elif not self.inputs:
                    LOG.info("Machine {}: Waiting for new input".format(
                        self.machine_id))
                    break
                else:
                    input_value = self.inputs.pop()
                    LOG.debug("Machine {}: Popping input {}".format(
                        self.machine_id, input_value))
                    self.memory[p1] = input_value
                self.ptr += 2
            elif opcode == 4:
                output, *_ = self.get_params(modes, 'r')
                LOG.debug("Machine {}: outputting: {}".format(
                    self.machine_id, output))
                self.outputs.append(output)
                self.ptr += 2
            elif opcode == 5:
                p1, p2 = self.get_params(modes, 'rr')
                if p1:
                    self.ptr = p2
                else:
                    self.ptr += 3
            elif opcode == 6:
                p1, p2 = self.get_params(modes, 'rr')
                if not p1:
                    self.ptr = p2
                else:
                    self.ptr += 3
            elif opcode == 7:
                p1, p2, p3 = self.get_params(modes, 'rrw')
                self.memory[p3] = int(p1 < p2)
                self.ptr += 4
            elif opcode == 8:
                p1, p2, p3 = self.get_params(modes, 'rrw')
                self.memory[p3] = int(p1 == p2)
                self.ptr += 4
            elif opcode == 99:
                self.finished = True
                LOG.info("Machine {} is halted".format(self.machine_id))
                break
            else:
                raise ValueError("Unknown opcode: {}".format(opcode))
