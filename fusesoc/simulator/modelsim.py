import os
from .simulator import Simulator
from fusesoc.config import Config
from fusesoc.utils import Launcher, pr_warn

VPI_MAKE_HEADER ="""#Generated by FuseSoC
CC ?= gcc
CFLAGS := -c -std=c99 -fPIC -fno-stack-protector -g -m32

LD ?= ld
LDFLAGS := -shared -E -melf_i386

RM ?= rm
INCS := -I{inc}

all: {modules}

clean: {clean_targets}
"""

VPI_MAKE_SECTION = """
{name}_ROOT := {root}
{name}_OBJS := {objs}
{name}_LIBS := {libs}
{name}_INCS := $(INCS) {incs}

$({name}_OBJS): %.o : $({name}_ROOT)/%.c
	$(CC) $(CFLAGS) $({name}_INCS) $<

{name}: $({name}_OBJS)
	$(LD) $(LDFLAGS) -o $@ $? $({name}_LIBS)

clean_{name}:
	$(RM) $({name}_OBJS) {name}
"""

class Modelsim(Simulator):

    def __init__(self, system):

        super(Modelsim, self).__init__(system)
        self.model_tech = os.getenv('MODEL_TECH')
        if not self.model_tech:
            raise RuntimeError("Environment variable MODEL_TECH was not found. It should be set to <modelsim install path>/bin")

    def _write_build_rtl_tcl_file(self, tcl_main):
        tcl_build_rtl  = open(os.path.join(self.work_root, "fusesoc_build_rtl.tcl"), 'w')

        (src_files, incdirs) = self._get_fileset_files(['sim', 'modelsim'])
        vlog_include_dirs = ['+incdir+'+d.replace('\\','/') for d in incdirs]

        libs = []
        for f in src_files:
            if not f.logical_name:
                f.logical_name = 'work'
            if not f.logical_name in libs:
                tcl_build_rtl.write("vlib {}\n".format(f.logical_name))
                libs.append(f.logical_name)
            if f.file_type.startswith("verilogSource") or \
               f.file_type.startswith("systemVerilogSource"):
                cmd = 'vlog'
                args = []

                if self.system.modelsim is not None:
                    args += self.system.modelsim.vlog_options

                for k, v in self.vlogdefine.items():
                    args += ['+define+{}={}'.format(k,v)]

                if f.file_type.startswith("systemVerilogSource"):
                    args += ['-sv']
                args += vlog_include_dirs
            elif f.file_type.startswith("vhdlSource"):
                cmd = 'vcom'
                if f.file_type.endswith("-87"):
                    args = ['-87']
                if f.file_type.endswith("-93"):
                    args = ['-93']
                if f.file_type.endswith("-2008"):
                    args = ['-2008']
                else:
                    args = []
            elif f.file_type == 'tclSource':
                cmd = None
                tcl_main.write("do {}\n".format(f.name))
            elif f.file_type == 'user':
                cmd = None
            else:
                _s = "{} has unknown file type '{}'"
                pr_warn(_s.format(f.name,
                                  f.file_type))
                cmd = None
            if cmd:
                if not Config().verbose:
                    args += ['-quiet']
                args += ['-work', f.logical_name]
                args += [f.name.replace('\\','/')]
                tcl_build_rtl.write("{} {}\n".format(cmd, ' '.join(args)))

    def _write_run_tcl_file(self):
        tcl_run = open(os.path.join(self.work_root, "fusesoc_run.tcl"), 'w')

        #FIXME: Handle failures. Save stdout/stderr
        vpi_options = []
        for vpi_module in self.vpi_modules:
            vpi_options += ['-pli', vpi_module['name']]

        args = ['vsim']
        if self.system.modelsim is not None:
            args += self.system.modelsim.vsim_options
        args += vpi_options
        args += self.toplevel.split()

        # Plusargs
        for key, value in self.plusarg.items():
            args += ['+{}={}'.format(key, value)]
        #Top-level parameters
        for key, value in self.vlogparam.items():
            args += ['-g{}={}'.format(key, value)]
        tcl_run.write(' '.join(args)+'\n')
        tcl_run.close()

    def _write_vpi_makefile(self):
        vpi_make = open(os.path.join(self.work_root, "Makefile"), 'w')
        _vpi_inc = self.model_tech+'/../include'
        _modules = [m['name'] for m in self.vpi_modules]
        _clean_targets = ' '.join(["clean_"+m for m in _modules])
        _s = VPI_MAKE_HEADER.format(inc=_vpi_inc,
                                    modules = ' '.join(_modules),
                                    clean_targets = _clean_targets)
        vpi_make.write(_s)

        for vpi_module in self.vpi_modules:
            _name = vpi_module['name']
            _root = vpi_module['root']
            _objs = [os.path.splitext(os.path.basename(s))[0]+'.o' for s in vpi_module['src_files']]
            _libs = vpi_module['libs']
            _incs = ['-I'+d for d in vpi_module['include_dirs']]
            _s = VPI_MAKE_SECTION.format(name=_name,
                                         root=_root,
                                         objs=' '.join(_objs),
                                         libs=' '.join(_libs),
                                         incs=' '.join(_incs))
            vpi_make.write(_s)

        vpi_make.close()

    def configure(self, args):
        super(Modelsim, self).configure(args)
        tcl_main = open(os.path.join(self.work_root, "fusesoc_main.tcl"), 'w')
        tcl_main.write("do fusesoc_build_rtl.tcl\n")

        self._write_build_rtl_tcl_file(tcl_main)
        if self.vpi_modules:
            self._write_vpi_makefile()
            tcl_main.write("make\n")
        tcl_main.close()
        self._write_run_tcl_file()


    def build(self):
        super(Modelsim, self).build()
        args = ['-c', '-do', 'do fusesoc_main.tcl; exit']
        Launcher(self.model_tech+'/vsim', args,
                 cwd      = self.work_root,
                 errormsg = "Failed to build simulation model. Log is available in '{}'".format(os.path.join(self.work_root, 'transcript'))).run()

    def run(self, args):
        super(Modelsim, self).run(args)

        args = ['-c', '-quiet', '-do', 'fusesoc_run.tcl', '-do', 'run -all']
        Launcher(self.model_tech+'/vsim', args,
                 cwd      = self.work_root,
                 errormsg = "Simulation failed. Simulation log is available in '{}'".format(os.path.join(self.work_root, 'transcript'))).run()

        super(Modelsim, self).done(args)
