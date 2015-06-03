import os
from fusesoc.config import Config
from fusesoc import utils
from fusesoc.utils import Launcher, pr_warn, pr_info


class Error(Exception):
    pass


class NoSuchItemError(Error):
    pass


class UnknownSection(Error):
    pass


class Section(object):

    TAG = None

    def __init__(self):
        self._members = {}
        self.export_files = []
        self.warnings = []

    def _add_member(self, name, _type, desc):
        self._members[name] = {'type' : _type, 'desc' : desc}
        setattr(self, name, _type())

    def export(self):
        return self.export_files

    def load_dict(self, items):
        for item in items:
            if item in self._members:
                _type = self._members.get(item)['type']
                if issubclass(_type, list):
                    setattr(self, item, items.get(item).split())
                else:
                    setattr(self, item, _type(items.get(item)))
            else:
                self.warnings.append(
                        'Unknown item "%(item)s" in section "%(section)s"' % {
                            'item': item, 'section': self.TAG})

    def __str__(self):
        s = ''
        for k,v in self._members.items():
            if isinstance(v.get('type'), list):
                s += k + ' : ' + ';'.join(getattr(self, item)) + '\n'
            elif isinstance(v.get('type'), str):
                s += k + ' : ' + getattr(self, k) + '\n'
        return s

class ToolSection(Section):
    def __init__(self):
        super(ToolSection, self).__init__()
        self._add_member('depend', list, "Dependencies")

class MainSection(Section):
    TAG = 'main'

    def __init__(self, items=None):
        super(MainSection, self).__init__()

        self._add_member('description', str, "Core description")
        self._add_member('depend', list, "Dependencies")
        self._add_member('simulators', list, "Supported simulators")
        self._add_member('patches', list, "FuseSoC-specific patches")

        if items:
            self.load_dict(items)

class VhdlSection(Section):

    TAG = 'vhdl'

    def __init__(self, items=None):
        super(VhdlSection, self).__init__()

        self._add_member('src_files', list, "VHDL source files")

        if items:
            self.load_dict(items)
            self.export_files = self.src_files

class VerilogSection(Section):

    TAG = 'verilog'

    def __init__(self, items=None):
        super(VerilogSection, self).__init__()

        self.include_dirs = []
        self.tb_include_dirs = []

        self._add_member('src_files'    , list, "Verilog source files")
        self._add_member('include_files', list, "Verilog include files")
        self._add_member('tb_src_files' , list, "Testbench verilog source files")
        self._add_member('tb_private_src_files', list, "Private testbench verilog source files")
        self._add_member('tb_include_files'    , list, "Testbench include files")

        if items:
            self.load_dict(items)
            if self.include_files:
                self.include_dirs  += list(set(map(os.path.dirname, self.include_files)))
            if self.tb_include_files:
                self.tb_include_dirs  += list(set(map(os.path.dirname, self.tb_include_files)))

            self.export_files = self.src_files + self.include_files + self.tb_src_files + self.tb_include_files + self.tb_private_src_files
    def __str__(self):
        s = ""
        if self.src_files:            s += "\nRTL source files :\n {}".format('\n '.join(self.src_files))
        if self.include_files:        s += "\nRTL include files :\n {}".format('\n '.join(self.include_files))
        if self.include_dirs:         s += "\nRTL Include directories :\n {}".format('\n '.join(self.include_dirs))
        if self.tb_src_files:         s += "\nPublic testbench source files :\n {}".format('\n '.join(self.tb_src_files))
        if self.tb_private_src_files: s += "\nPrivate testbench source files :\n {}".format('\n '.join(self.tb_private_src_files))
        if self.tb_include_files:     s += "\nTestbench include files :\n {}".format('\n '.join(self.tb_include_files))
        if self.tb_include_dirs:      s += "\nTestbench include directories :\n {}".format('\n '.join(self.tb_include_dirs))

        return s

class VpiSection(Section):

    TAG = 'vpi'

    def __init__(self, items=None):
        super(VpiSection, self).__init__()

        self.include_dirs = []

        self._add_member('src_files', list, "VPI C files")
        self._add_member('include_files', list, "VPI C include files")
        self._add_member('libs', list, "VPI C libraries")

        if items:
            self.load_dict(items)
            if self.include_files:
                self.include_dirs  += list(set(map(os.path.dirname, self.include_files)))

            self.export_files = self.src_files + self.include_files


class ModelsimSection(ToolSection):

    TAG = 'modelsim'

    def __init__(self, items=None):
        super(ModelsimSection, self).__init__()

        self._add_member('vlog_options', list, "Modelsim verilog compile options")
        self._add_member('vsim_options', list, "Modelsim runtime options")

        if items:
            self.load_dict(items)

class IcarusSection(ToolSection):

    TAG = 'icarus'

    def __init__(self, items=None):
        super(IcarusSection, self).__init__()

        self._add_member('iverilog_options', list, "Icarus verilog compile options")

        if items:
            self.load_dict(items)

    def __str__(self):
        s = ""
        if self.depend: s += "Icarus-specific dependencies : {}\n".format(' '.join(self.depend))
        if self.iverilog_options: s += "Icarus compile options : {}\n".format(' '.join(self.iverilog_options))
        return s


class VerilatorSection(ToolSection):

    TAG = 'verilator'

    def __init__(self, items=None):
        super(VerilatorSection, self).__init__()

        self.include_dirs = []
        self.archive = False
        self._object_files = []

        self._add_member('verilator_options', list, "Verilator build options")
        self._add_member('src_files'        , list, "Verilator testbench source files")
        self._add_member('include_files'    , list, "Verilator testbench include files")
        self._add_member('define_files'     , list, "Verilator testbench include files (converts to verilog include files)")
        self._add_member('libs'             , list, "Verilator C/C++ libraries")

        self._add_member('tb_toplevel', str, 'Testbench top-level C/C++/SC file')
        self._add_member('source_type', str, 'Testbench source code language (systemC/Cpp)')
        self._add_member('top_module' , str, 'verilog top-level module')

        if items:
            self.load_dict(items)
            self.include_dirs  = list(set(map(os.path.dirname, self.include_files)))
            if self.src_files:
                self._object_files = [os.path.splitext(os.path.basename(s))[0]+'.o' for s in self.src_files]
                self.archive = True
                self.export_files = self.src_files + self.include_files


    def __str__(self):
        s = """Verilator options       : {verilator_options}
Testbench source files  : {src_files}
Testbench include files : {include_files}
Testbench define files  : {define_files}
External libraries      : {libs}
Testbench top level     : {tb_toplevel}
Testbench source type   : {source_type}
Verilog top module      : {top_module}
"""
        return s.format(verilator_options=' '.join(self.verilator_options),
                        src_files = ' '.join(self.src_files),
                        include_files=' '.join(self.include_files),
                        define_files=' '.join(self.define_files),
                        libs=' '.join(self.libs),
                        tb_toplevel=self.tb_toplevel,
                        source_type=self.source_type,
                        top_module=self.top_module)

    def build(self, core, sim_root, src_root):
        if self.source_type == 'C' or self.source_type == '':
            self.build_C(core, sim_root, src_root)
        elif self.source_type == 'CPP':
            self.build_CPP(core, sim_root, src_root)
        elif self.source_type == 'systemC':
            self.build_SysC(core, sim_root, src_root)
        else:
            raise Source(self.source_type)

        if self._object_files:
            args = []
            args += ['rvs']
            args += [core+'.a']
            args += self._object_files
            l = Launcher('ar', args,
                     cwd=sim_root)
            if Config().verbose:
                pr_info("  linker working dir: " + sim_root)
                pr_info("  linker command: ar " + ' '.join(args))
            l.run()
            print()

    def build_C(self, core, sim_root, src_root):
        args = ['-c']
        args += ['-std=c99']
        args += ['-I'+src_root]
        args += ['-I'+os.path.join(src_root, core, s) for s in self.include_dirs]
        for src_file in self.src_files:
            pr_info("Compiling " + src_file)
            l = Launcher('gcc',
                     args + [os.path.join(src_root, core, src_file)],
                         cwd=sim_root,
                         stderr = open(os.path.join(sim_root, 'gcc.err.log'),'a'),
                         stdout = open(os.path.join(sim_root, 'gcc.out.log'),'a'))
            if Config().verbose:
                pr_info("  C compilation working dir: " + sim_root)
                pr_info("  C compilation command: gcc " + ' '.join(args) + ' ' + os.path.join(src_root, core, src_file))
            l.run()

    def build_CPP(self, core, sim_root, src_root):
        verilator_root = utils.get_verilator_root()
        if verilator_root is None:
            verilator_root = utils.get_verilator_root()
        args = ['-c']
        args += ['-I'+src_root]
        args += ['-I'+os.path.join(src_root, core, s) for s in self.include_dirs]
        args += ['-I'+os.path.join(verilator_root,'include')]
        args += ['-I'+os.path.join(verilator_root,'include', 'vltstd')]
        for src_file in self.src_files:
            pr_info("Compiling " + src_file)
            l = Launcher('g++', args + [os.path.join(src_root, core, src_file)],
                         cwd=sim_root,
                         stderr = open(os.path.join(sim_root, 'g++.err.log'),'a'))
            if Config().verbose:
                pr_info("  C++ compilation working dir: " + sim_root)
                pr_info("  C++ compilation command: g++ " + ' '.join(args) + ' ' + os.path.join(src_root, core, src_file))
            l.run()

    def build_SysC(self, core, sim_root, src_root):
        verilator_root = utils.get_verilator_root()
        args = ['-I.']
        args += ['-MMD']
        args += ['-I'+src_root]
        args += ['-I'+s for s in self.include_dirs]
        args += ['-Iobj_dir']
        args += ['-I'+os.path.join(verilator_root,'include')]
        args += ['-I'+os.path.join(verilator_root,'include', 'vltstd')]  
        args += ['-DVL_PRINTF=printf']
        args += ['-DVM_TRACE=1']
        args += ['-DVM_COVERAGE=0']
        if os.getenv('SYSTEMC_INCLUDE'):
            args += ['-I'+os.getenv('SYSTEMC_INCLUDE')]
        if os.getenv('SYSTEMC'):
            args += ['-I'+os.path.join(os.getenv('SYSTEMC'),'include')]
        args += ['-Wno-deprecated']
        if os.getenv('SYSTEMC_CXX_FLAGS'):
             args += [os.getenv('SYSTEMC_CXX_FLAGS')]
        args += ['-c']
        args += ['-g']

        for src_file in self.src_files:
            pr_info("Compiling " + src_file)
            l = Launcher('g++', args + [os.path.join(src_root, core, src_file)],
                         cwd=sim_root,
                         stderr = open(os.path.join(sim_root, 'g++.err.log'),'a'))
            if Config().verbose:
                pr_info("  SystemC compilation working dir: " + sim_root)
                pr_info("  SystemC compilation command: g++ " + ' '.join(args) + ' ' + os.path.join(src_root, core, src_file))
            l.run()

class IseSection(ToolSection):

    TAG = 'ise'

    def __init__(self, items=None):
        super(IseSection, self).__init__()

        self._add_member('ucf_files' , list, "UCF constraint files")
        self._add_member('tcl_files' , list, "Extra TCL scripts")
        self._add_member('family'    , str, 'FPGA device family')
        self._add_member('device'    , str, 'FPGA device identifier')
        self._add_member('package'   , str, 'FPGA device package')
        self._add_member('speed'     , str, 'FPGA device speed grade')
        self._add_member('top_module', str, 'RTL top-level module')

        if items:
            self.load_dict(items)
            self.export_files = self.ucf_files

class QuartusSection(ToolSection):

    TAG = 'quartus'

    def __init__(self, items=None):
        super(QuartusSection, self).__init__()

        self._add_member('qsys_files', list, "Qsys IP description files")
        self._add_member('sdc_files' , list, "SDC constraint files")
        self._add_member('tcl_files', list, "Extra script files")

        self._add_member('quartus_options', str, 'Quartus command-line options')
        self._add_member('family'         , str, 'FPGA device family')
        self._add_member('device'         , str, 'FPGA device identifier')
        self._add_member('top_module'     , str, 'RTL top-level module')

        if items:
            self.load_dict(items)
            self.export_files = self.qsys_files + self.sdc_files


def load_section(config, section_name, name='<unknown>'):
    cls = SECTION_MAP.get(section_name)
    if cls is None:
        return None

    items = config.get_section(section_name)
    section = cls(items)
    if section.warnings:
        for warning in section.warnings:
            pr_warn('Warning: %s in %s' % (warning, name))
    return section


def load_all(config, name='<unknown>'):
    for section_name in config.sections():
        section = load_section(config, section_name, name)
        if section:
            yield section


SECTION_MAP = {}


def _register_subclasses(parent):
    for cls in parent.__subclasses__():
        _register_subclasses(cls)
        if cls.TAG is None:
            continue
        SECTION_MAP[cls.TAG] = cls


_register_subclasses(Section)
