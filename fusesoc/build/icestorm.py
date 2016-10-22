import os.path
import shutil
from fusesoc import utils

from fusesoc.build.backend import Backend
class Icestorm(Backend):

    MAKEFILE_TEMPLATE = """#Auto generated by FuseSoC
include config.mk

all: $(TARGET).bin

%.blif: %.ys
	yosys -q -s $?
%.txt: $(PCF_FILE) %.blif
	arachne-pnr $(ARACHNE_PNR_OPTIONS) -q -p $? -o $@
%.bin: %.txt
	icepack $< $@

clean:
	rm -f $(TARGET).blif $(TARGET).txt $(TARGET).bin
"""

    CONFIG_MK_TEMPLATE = """#Auto generated by FuseSoC
TARGET   := {target}
PCF_FILE := {pcf_file}
ARACHNE_PNR_OPTIONS := {arachne_pnr_options}
"""

    TOOL_NAME = 'icestorm'

    def configure(self, args):
        super(Icestorm, self).configure(args)
        self._write_config_files()

    def _write_config_files(self):
        # Write Makefile
        with open(os.path.join(self.work_root, 'Makefile'), 'w') as makefile:
            makefile.write(self.MAKEFILE_TEMPLATE)


        # Write config.mk
        _pcf_file = os.path.relpath(os.path.join(self.src_root,
                                                 self.system.sanitized_name,
                                                 self.backend.pcf_file[0].name),
                                    self.work_root)

        with open(os.path.join(self.work_root, 'config.mk'), 'w') as config_mk:
            config_mk.write(self.CONFIG_MK_TEMPLATE.format(
                target              =  self.system.sanitized_name,
                pcf_file            = _pcf_file,
                arachne_pnr_options = ' '.join(self.backend.arachne_pnr_options)))

        # Write yosys script file
        (src_files, incdirs) = self._get_fileset_files(['synth', 'icestorm'])
        with open(os.path.join(self.work_root, self.system.sanitized_name+'.ys'), 'w') as yosys_file:
            yosys_file.write("verilog_defaults -push\n")
            yosys_file.write("verilog_defaults -add -defer\n")
            if incdirs:
                yosys_file.write("verilog_defaults -add {}\n".format(' '.join(['-I'+d for d in incdirs])))

            for f in src_files:
                if f.file_type in ['verilogSource']:
                    yosys_file.write("read_verilog {}\n".format(
                                                                   f.name))
            for key, value in self.vlogparam.items():
                _s = "chparam -set {} {} $abstract\{}\n"
                yosys_file.write(_s.format(key,
                                           value,
                                           self.backend.top_module))
            if self.backend.top_module:
                _top = "-top " + self.backend.top_module
            yosys_file.write("verilog_defaults -pop\n")
            yosys_file.write("synth_ice40")
            yosys_file.write(" -blif {}.blif".format(self.system.sanitized_name))
            if self.backend.top_module:
                yosys_file.write(" -top " + self.backend.top_module)
            yosys_file.write("\n")


    def build(self, args):
        super(Icestorm, self).build(args)

        utils.Launcher('make', cwd = self.work_root).run()

        super(Icestorm, self).done()
