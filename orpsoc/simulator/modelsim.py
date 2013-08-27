import os
import subprocess
from .simulator import Simulator

class Modelsim(Simulator):

    def __init__(self, system):
        super(Modelsim, self).__init__(system)
        self.model_tech = os.getenv('MODEL_TECH')
        if not self.model_tech:
            print("Environment variable MODEL_TECH was not found. It should be set to <modelsim install path>/bin")
            exit(1)
        self.sim_root = os.path.join(self.build_root, 'sim-modelsim')
        
    def configure(self):
        super(Modelsim, self).configure()
        self._write_config_files()

    def _write_config_files(self):
        self.cfg_file = self.system.name+'.scr'

        f = open(os.path.join(self.sim_root,self.cfg_file),'w')

        for include_dir in self.verilog.include_dirs:
            f.write("+incdir+" + include_dir + '\n')
        for src_file in self.verilog.src_files:
            f.write(src_file + '\n')
        for include_dir in self.verilog.tb_include_dirs:
            f.write("+incdir+" + include_dir + '\n')
        for src_file in self.verilog.tb_src_files:
            f.write(src_file + '\n')

        f.close()

    def build(self):
        super(Modelsim, self).build()

        #FIXME: Handle failures. Save stdout/stderr. Build vmem file from elf file argument
        try:
            subprocess.check_call([self.model_tech+'/vlib', 'work'],
                                  cwd = self.sim_root)

        except OSError:
            print("Error: Command vlib not found. Make sure it is in $PATH")
            exit(1)
        except CalledProcessError:
            print("Error: Failed to create library work")
            exit(1)

        try:
            logfile = os.path.join(self.sim_root, 'vlog.log')
            subprocess.check_call([self.model_tech+'/vlog', '-f', self.cfg_file, '-quiet', '-l', logfile] +
                                  self.system.vlog_options,
                            cwd = self.sim_root)
        except OSError:
            print("Error: Command vlog not found. Make sure it is in $PATH")
            exit(1)
        except subprocess.CalledProcessError:
            print("Error: Failed to compile simulation model. Compile log is available in " + logfile)
            exit(1)

        for vpi_module in self.vpi_modules:
            objs = []
            for src_file in vpi_module['src_files']:
                try:
                    subprocess.check_call(['gcc', '-c', '-fPIC', '-g','-m32','-DMODELSIM_VPI'] +
                                          ['-I'+self.model_tech+'/../include'] +
                                          ['-I'+s for s in vpi_module['include_dirs']] +
                                          [src_file],
                                          cwd = self.sim_root,
                                          stdin=subprocess.PIPE)
                except OSError:
                    print("Error: Command gcc not found. Make sure it is in $PATH")
                    exit(1)
                except subprocess.CalledProcessError:
                    print("Error: Compilation of "+src_file + "failed")
                    exit(1)

                object_files = [os.path.splitext(os.path.basename(s))[0]+'.o' for s in vpi_module['src_files']]
            try:
                subprocess.check_call(['ld', '-shared','-E','-melf_i386','-o',vpi_module['name']] +
                                      object_files,
                                      cwd = self.sim_root,
                                      stdin=subprocess.PIPE)
            except OSError:
                print("Error: Command ld not found. Make sure it is in $PATH")
                exit(1)
            except subprocess.CalledProcessError:
                print("Error: Linking of "+vpi_module['name'] + " failed")
                exit(1)

    def run(self, args):
        super(Modelsim, self).run(args)

        #FIXME: Handle failures. Save stdout/stderr
        vpi_options = []
        for vpi_module in self.vpi_modules:
            vpi_options += ['-pli', vpi_module['name']]
        try:
            logfile = os.path.join(self.sim_root, 'vsim.log')
            subprocess.check_call([self.model_tech+'/vsim', '-c', '-do', 'run -all'] +
                                  ['-l', logfile] +
                                  self.system.vsim_options +
                                  vpi_options +
                                  ['work.'+self.toplevel] +
                                  ['+'+s for s in self.plusargs],
                                  cwd = self.sim_root,
                                  stdin=subprocess.PIPE)
        except OSError:
            print("Error: Command vsim not found. Make sure it is in $PATH")
            exit(1)
        except subprocess.CalledProcessError:
            print("Error: Simulation failed. Simulation log is available in " + logfile)
            exit(1)
