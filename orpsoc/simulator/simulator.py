from orpsoc.config import Config
import shutil
import os
class Simulator(object):

    def __init__(self, system):
        config = Config()
        self.system = system
        self.build_root = os.path.join(config.build_root, self.system.name)
        self.cores_root = config.cores_root
        self.systems_root = config.systems_root

        self.src_root = os.path.join(self.build_root, 'src')

        self.include_dirs = []
        self.src_files = []

        for core_name in self.system.get_cores():
            core = self.system.cores[core_name]
            if core.verilog:
                self.include_dirs += [os.path.join(self.src_root, core_name, d) for d in core.verilog.include_dirs]
                self.include_dirs += [os.path.join(self.src_root, core_name, d) for d in core.verilog.tb_include_dirs]
                self.src_files    += [os.path.join(self.src_root, core_name, f) for f in core.verilog.src_files]
                self.src_files    += [os.path.join(self.src_root, core_name, f) for f in core.verilog.tb_src_files]

    def configure(self):
        if os.path.exists(self.sim_root):
            shutil.rmtree(self.sim_root)
        os.makedirs(self.sim_root)

        self.system.setup_cores()

        for name, core in self.system.get_cores().items():
            print("Preparing " + name)
            dst_dir = os.path.join(Config().build_root, self.system.name, 'src', name)
            core.setup()
            core.export(dst_dir)
            core.patch(dst_dir)

    def build(self):
        self.vpi_modules = []
        for name, core in self.system.get_cores().items():
            if core.vpi:
                vpi_module = {}
                core_root = os.path.join(self.src_root, name)
                vpi_module['include_dirs']  = [os.path.join(core_root, d) for d in core.vpi.include_dirs]
                vpi_module['src_files']     = [os.path.join(core_root, f) for f in core.vpi.src_files]
                vpi_module['name']          = core.vpi.name
                self.vpi_modules += [vpi_module]

    def run(self, args):

        #FIXME: Smarter plusargs handling
        self.plusargs = []
        
        vmem_file=os.path.abspath(args.testcase[0])
        if not os.path.exists(vmem_file):
            print("Error: Couldn't find test case " + vmem_file)
            exit(1)
        self.plusargs += ['testcase='+vmem_file]
        if args.timeout:
            print("Setting timeout to "+str(args.timeout[0]))
            self.plusargs += ['timeout='+str(args.timeout[0])]

        if args.enable_dbg:
            print("Enabling debug interface")
            self.plusargs += ['enable_dbg']
