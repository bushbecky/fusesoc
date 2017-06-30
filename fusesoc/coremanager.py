import logging
import os

from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints import PrettyPackageStringParser, Requirement
from simplesat.dependency_solver import DependencySolver
from simplesat.errors import NoPackageFound, SatisfiabilityError
from simplesat.pool import Pool
from simplesat.repository import Repository
from simplesat.request import Request

from fusesoc.core import Core

logger = logging.getLogger(__name__)

class DependencyError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CoreDB(object):
    def __init__(self):
        self._cores = {}

    #simplesat doesn't allow ':', '-' or leading '_'
    def _package_name(self, vlnv):
        _name = "{}_{}_{}".format(vlnv.vendor,
                                  vlnv.library,
                                  vlnv.name).lstrip("_")
        return _name.replace('-','__')

    def _package_version(self, vlnv):
        return "{}-{}".format(vlnv.version,
                              vlnv.revision)

    def _parse_depend(self, depends):
        #FIXME: Handle conflicts
        deps = []
        _s = "{} {} {}"
        for d in depends:
            deps.append(_s.format(self._package_name(d),
                                  d.relation,
                                  self._package_version(d)))
        return ", ".join(deps)

    def add(self, core):
        name = str(core.name)
        logger.debug("Adding core " + name)
        if name in self._cores:
            _s = "Replacing {} in {} with the version found in {}"
            logger.debug(_s.format(name,
                                   self._cores[name].core_root,
                                   core.core_root))
        self._cores[name] = core

    def find(self, vlnv=None):
        if vlnv:
            found = self._solve(vlnv, only_matching_vlnv=True)[-1]
        else:
            found = list(self._cores.values())
        return found

    def solve(self, top_core, flags):
        return self._solve(top_core, flags)

    def _solve(self, top_core, flags={}, only_matching_vlnv=False):
        def eq_vln(this, that):
            return \
                this.vendor  == that.vendor and \
                this.library == that.library and \
                this.name    == that.name

        repo = Repository()
        for core in self._cores.values():
            if only_matching_vlnv:
                if not eq_vln(core.name, top_core):
                    continue

            package_str = "{} {}-{}".format(self._package_name(core.name),
                                            core.name.version,
                                            core.name.revision)
            if not only_matching_vlnv:
                _depends = core.get_depends(flags)
                if _depends:
                    _s = "; depends ( {} )"
                    package_str += _s.format(self._parse_depend(_depends))
            parser = PrettyPackageStringParser(EnpkgVersion.from_string)

            package = parser.parse_to_package(package_str)
            package.core = core

            repo.add_package(package)

        request = Request()
        _top_dep = "{} {} {}".format(self._package_name(top_core),
                                     top_core.relation,
                                     self._package_version(top_core))
        requirement = Requirement._from_string(_top_dep)
        request.install(requirement)
        installed_repository = Repository()
        pool = Pool([repo])
        pool.add_repository(installed_repository)
        solver = DependencySolver(pool, [repo], installed_repository)

        try:
            transaction = solver.solve(request)
        except SatisfiabilityError as e:
            msg = "UNSATISFIABLE: {}"
            raise RuntimeError(msg.format(e.unsat.to_string(pool)))
        except NoPackageFound as e:
            raise DependencyError(top_core.name)

        return [op.package.core for op in transaction.operations]

class CoreManager(object):
    _instance = None
    _cores_root = []

    db = CoreDB()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CoreManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def load_core(self, file):
        if os.path.exists(file):
            try:
                core = Core(file)
                self.db.add(core)
            except SyntaxError as e:
                w = "Failed to parse " + file + ": " + e.msg
                logger.warning(w)
            except ImportError as e:
                logger.warning('Failed to register "{}" due to unknown provider: {}'.format(file, str(e)))

    def load_cores(self, path):
        if path:
            logger.debug("Checking for cores in " + path)
        if os.path.isdir(path) == False:
            raise IOError(path + " is not a directory")
        for root, dirs, files in os.walk(path, followlinks=True):
            for f in files:
                if f.endswith('.core'):
                    d = os.path.basename(root)
                    self.load_core(os.path.join(root, f))
                    del dirs[:]

    def add_cores_root(self, path):
        if path is None:
            return
        elif not isinstance(path, list):
            path = [path]
        for p in path:
            if not p:
                # skip empty entries
                continue
            abspath = os.path.abspath(os.path.expanduser(p))
            if not abspath in self._cores_root:
                self.load_cores(os.path.expanduser(p))
                self._cores_root += [abspath]

    def get_cores_root(self):
        return self._cores_root

    def get_depends(self, core, flags):
        resolved_core = self.db.find(core)
        return self.db.solve(resolved_core.name, flags)

    def get_cores(self):
        return {str(x.name) : x for x in self.db.find()}

    def get_core(self, name):
        c = self.db.find(name)
        c.name.relation = "=="
        return c

    def get_eda_api(self, vlnv, flags):

        parameters   = []

        cores = self.get_depends(vlnv, flags)

        _flags = flags.copy()
        for core in cores:
            _flags['is_toplevel'] = (core.name == vlnv)

            #Extract parameters
            for param in core.get_parameters(_flags):
                parameters.append ({
                    'datatype'    : param.datatype,
                    'default'     : param.default,
                    'description' : param.description,
                    'name'        : param.name,
                    'paramtype'   : param.paramtype})
        top_core = cores[-1]
        return {
            'name'         : top_core.sanitized_name,
            'parameters'   : parameters,
            'toplevel'     : top_core.get_toplevel(flags)
        }
