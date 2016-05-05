import re

class TapConverter(object):

    def __init__(self, source):
        self.source = source

    @staticmethod
    def from_file(self, filename):
        content = open(filename, 'r').read()
        return TapConverter(content)

    def replace_code(self, input, search, replace):
        return input.replace(search, replace)

    def get_largest_x(self):
        largestX = 0.0

        matches = re.findall('X([\d.]+)', self.source, re.MULTILINE)
        if matches:
            for match in matches:
                largestX = max(largestX, float(match))

        return largestX

    def get_gcode(self):

        input = self.source

        input = self.replace_code(input, "M30", "G92 X0")
        input = self.replace_code(input, "F3600.0", "F2000.0")
        input = self.replace_code(input, "G00 X0.000 Y0.000", "G90")
        input = self.replace_code(input, "G00", "G01")

        input = re.sub(r'G01\s+Z0\.500\s+F1200\.0', 'M8', input, flags=re.MULTILINE)
        input = re.sub(r'G01\s+Z-6\.000', 'M9 G4 P1', input, flags=re.MULTILINE)

        largest_x = self.get_largest_x()
        input = re.sub(r'G01\s+Z-20\.000', 'G1 X%.3f F2000' % (largest_x + 30,), input, flags=re.MULTILINE)

        input = self.replace_code(input, "Z-6.000", "F2000")

        return '\n'.join(input.split('\n')[5:])