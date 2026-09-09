import os, sys, time, resource, signal, pathlib, importlib.abc, importlib.machinery
import json, hashlib, traceback, stat

BASE = pathlib.Path('/Users/maxghenis/PolicyEngine/_worktrees/microcosm-us-joint-puma-county-cd-20260909')
RUN = pathlib.Path('/private/tmp/us-joint-geography-invented-root-20260909')
ENV = pathlib.Path('/Users/maxghenis/PolicyEngine/_worktrees/microcosm-us-launch-current-main-20260905/.venv')
SITE = ENV / 'lib/python3.14/site-packages'
CONFIG_SHA256 = '6487f28cc0ad34d03bf511640c9e1bd60f669085f9bf2e3f72e27fdeb7ccfb36'
EXE_SHA256 = 'bf4ea26231212e330b8e9b6f24969a30f894fec88665bf42754070d114ac7fc6'
START = time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
signal.alarm(180)
assert sys.version_info[:3] == (3, 14, 4)
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
EXECUTABLE = pathlib.Path(sys.executable)
assert EXECUTABLE == ENV / 'bin/python'
assert pathlib.Path(__file__) == RUN / 'run.py'
assert sys.argv[1:] == ['joint-geography-v1']
label = sys.argv[1]
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[name] = '1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
os.environ['TZ'] = 'UTC'
os.environ['TMPDIR'] = str(RUN)
os.environ.pop('POLICYENGINE_UK_DEFAULT_DATASET', None)
os.chdir(RUN)
assert RUN.resolve() == RUN
sys.pycache_prefix = str(RUN / 'bytecode-cache')
assert not pathlib.Path(sys.pycache_prefix).exists()

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

assert digest(RUN / 'EXECUTION-CONFIG.json') == CONFIG_SHA256
CONFIG = json.loads((RUN / 'EXECUTION-CONFIG.json').read_text())
assert CONFIG['run_root'] == str(RUN) and CONFIG['source_root'] == str(BASE)
assert CONFIG['interpreter'] == str(EXECUTABLE) and CONFIG['interpreter_sha256'] == EXE_SHA256
assert CONFIG['limits'] == {'cpu_seconds':120,'wall_seconds':180,'native_threads':1,'children':0,'network':False,'RSS':'final peak reporting only'}
assert CONFIG['automatic_retry'] is False
APPROVAL_PATH = RUN / 'ROOT-EXECUTION-APPROVAL.json'
APPROVAL = json.loads(APPROVAL_PATH.read_text())
assert APPROVAL == {
    'protocol':'owned.catalogue-controls-execution-approval.v1',
    'execution_approved':True,
    'guard_sha256':digest(RUN / 'run.py'),
    'configuration_sha256':CONFIG_SHA256,
    'implementation_manifest_sha256':CONFIG['implementation_manifest_sha256'],
    'resources_approved':CONFIG['allowed_resources'],
    'automatic_retry':False,
    'scope':CONFIG['scope'],
}
for name, expected in CONFIG['owned_inputs'].items():
    assert pathlib.PurePosixPath(name).name == name
    assert digest(RUN / name) == expected, name
SOURCE = json.loads((RUN / 'SOURCE-HASHES.json').read_text())
RUNTIME = json.loads((RUN / 'RUNTIME-CODE-PINS.json').read_text())
REFUSAL_LIMITS = json.loads((RUN / 'REFUSAL-LIMITS.json').read_text())
assert len(SOURCE) == CONFIG['source_pin_count']
assert len(RUNTIME) == CONFIG['runtime_code_pin_count'] == 6
assert (RUN / 'head.txt').read_text().strip() == CONFIG['source_head'] == 'a19582bd918829858a117f0d6aafa2b994e856ec'
assert CONFIG['selected_tests'] == ['test_us_puma_ladder.py', 'test_us_puma_ladder_sources.py']
assert CONFIG['expected_tests'] == 55
PIN_ROWS = {}
def add_pin(name, path, expected):
    assert name not in PIN_ROWS
    PIN_ROWS[name] = (path, expected)
for name, expected in SOURCE.items():
    relative = pathlib.PurePosixPath(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    add_pin('source/' + name, BASE / name, expected)
for number, (path, expected) in enumerate(sorted(RUNTIME.items())):
    assert pathlib.Path(path).is_relative_to(SITE) or pathlib.Path(path).is_relative_to(pathlib.Path(sys.base_prefix))
    add_pin('runtime-code/' + str(number), pathlib.Path(path), expected)
for number, (path, expected) in enumerate(sorted(CONFIG['allowed_resources'].items())):
    add_pin('resource/' + str(number), pathlib.Path(path), expected)
for name, expected in CONFIG['owned_inputs'].items():
    add_pin('owned/' + name, RUN / name, expected)
add_pin('owned/EXECUTION-CONFIG.json', RUN / 'EXECUTION-CONFIG.json', CONFIG_SHA256)
add_pin('owned/run.py', RUN / 'run.py', APPROVAL['guard_sha256'])
add_pin('owned/ROOT-EXECUTION-APPROVAL.json', APPROVAL_PATH, digest(APPROVAL_PATH))
add_pin('interpreter', EXECUTABLE, EXE_SHA256)
EXPECTED = {name: row[1] for name, row in PIN_ROWS.items()}
PIN_PATHS = {row[0] for row in PIN_ROWS.values()}
RESOURCE_PATHS = {pathlib.Path(path) for path in CONFIG['allowed_resources']}
CODE_ROOTS = (BASE, SITE, pathlib.Path(sys.base_prefix), pathlib.Path('/Library/Frameworks/Python.framework/Versions/3.14'))
BLOCKED, READS, CODE_READS, SYMLINK_EVENTS = [], {'before':set(),'runtime':set(),'after':set()}, set(), []
PHASE = 'before'
_STAT, _LSTAT = os.stat, os.lstat

def absolute(value):
    return pathlib.Path(os.path.abspath(os.fsdecode(value)))
def owned(value):
    if not isinstance(value, (str, bytes, os.PathLike)): return False
    path = absolute(value)
    if not path.is_relative_to(RUN): return False
    current = path
    while current.is_relative_to(RUN):
        try:
            if stat.S_ISLNK(_LSTAT(current).st_mode): return False
        except FileNotFoundError: pass
        current = current.parent
    return True

class CountryAndOriginGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition('.')[0].startswith('policyengine') or fullname.startswith('microcosm.build.uk_runtime'):
            BLOCKED.append('engine:' + fullname)
            raise RuntimeError('Country engine import forbidden: ' + fullname)
        if fullname.partition('.')[0] in {'h5py','tables','microunit'}:
            BLOCKED.append('source-issuer:' + fullname)
            raise ImportError('Joint geography controls do not admit HDF or source issuer dependencies')
        if fullname.startswith('microcosm.'):
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            if spec is not None and spec.origin not in (None, 'namespace'):
                origin = absolute(spec.origin)
                if not origin.is_relative_to(BASE):
                    BLOCKED.append('origin:' + fullname + ':' + str(origin))
                    raise ImportError('Project import from another checkout refused')
            return spec
sys.meta_path.insert(0, CountryAndOriginGuard())

def audit(event, args):
    if event in ('os.listdir','os.scandir') and args and isinstance(args[0], (str,bytes)):
        if not any(absolute(args[0]).is_relative_to(root) for root in (*CODE_ROOTS, RUN)):
            BLOCKED.append('directory:' + str(args[0])); raise PermissionError('Unrelated directory enumeration refused')
    if (event.startswith('socket.') and event != 'socket.gethostname') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.exec','os.fork','pty.spawn'}:
        BLOCKED.append(event); raise PermissionError('External operation refused: ' + event)
    if event == 'os.putenv' and os.fsdecode(args[0]) == 'POLICYENGINE_UK_DEFAULT_DATASET':
        BLOCKED.append('default-dataset-env'); raise PermissionError('Default dataset route refused')
    if event == 'os.symlink':
        detail = [os.fsdecode(v) if isinstance(v,(str,bytes)) and len(v)<=4096 else '<invalid-path>' for v in args[:2]]
        detail.append(args[2] if len(args)==3 and type(args[2]) is int else '<invalid-dir-fd>')
        if len(SYMLINK_EVENTS) < 39:
            SYMLINK_EVENTS.append(detail)
            BLOCKED.append('symlink:' + json.dumps(detail, ensure_ascii=True, separators=(',',':')))
        else: BLOCKED.append('symlink:observation-limit')
        raise PermissionError('All symlink creation refused')
    one = {'os.remove','os.rmdir','os.mkdir','os.chmod','os.chown','os.truncate','os.utime','os.chdir'}
    two = {'os.rename','os.link'}
    if event in one | two:
        if not all(owned(value) for value in (args[:2] if event in two else args[:1])):
            BLOCKED.append('mutation:' + event); raise PermissionError('Mutation outside owned root refused')
    if event == 'open' and isinstance(args[0], (str,bytes)):
        path = absolute(args[0])
        if str(path).endswith(('.err','.lane.log')):
            BLOCKED.append(str(path)); raise RuntimeError('Forbidden log')
        if owned(path) or path == pathlib.Path('/dev/null'): return
        mode, flags = args[1], args[2]
        if (isinstance(mode,str) and any(v in mode for v in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            BLOCKED.append('write:' + str(path)); raise PermissionError('Write outside owned root refused')
        if path in PIN_PATHS:
            if path in RESOURCE_PATHS: READS[PHASE].add(str(path))
            elif path.suffix == '.py': CODE_READS.add(str(path))
            return
        if any(path.is_relative_to(root) for root in CODE_ROOTS):
            if path.suffix in {'.py','.pyc','.so','.dylib'}:
                CODE_READS.add(str(path)); return
            if path.name in {'METADATA','WHEEL','entry_points.txt','top_level.txt','py.typed'} and any(part.endswith('.dist-info') for part in path.parts): return
        BLOCKED.append(str(path)); raise PermissionError('Read blocked before open: ' + str(path))

def metadata_allowed(value):
    if isinstance(value,int): return True
    path = absolute(value)
    if str(path).endswith(('.err','.lane.log')): return False
    if path.name == 'RECORD' and path not in PIN_PATHS: return False
    if path == EXECUTABLE or EXECUTABLE.is_relative_to(path): return True
    if owned(path) or path in PIN_PATHS or path == pathlib.Path(sys.base_prefix)/'lib/python3.14': return True
    if any(root.is_relative_to(path) for root in (*CODE_ROOTS,RUN)): return True
    if any(path.is_relative_to(root) for root in CODE_ROOTS):
        return path.suffix in {'','.py','.pyc','.so','.dylib','.dist-info','.git'} or path.name in {'METADATA','WHEEL','entry_points.txt','top_level.txt','py.typed'}
    return False

def guarded_stat(path,*args,**kwargs):
    if not metadata_allowed(path):
        BLOCKED.append('stat:' + os.fsdecode(path)); raise PermissionError('Metadata blocked before stat')
    return _STAT(path,*args,**kwargs)
def guarded_lstat(path,*args,**kwargs):
    if not metadata_allowed(path):
        BLOCKED.append('lstat:' + os.fsdecode(path)); raise PermissionError('Metadata blocked before lstat')
    return _LSTAT(path,*args,**kwargs)
os.stat, os.lstat = guarded_stat, guarded_lstat
sys.addaudithook(audit)
sys.path[:0] = [str(BASE / ('packages/microcosm-' + shard + '/src')) for shard in ('frame','fit','calibrate','build','data','graph')] + [str(SITE)]
sys.path.insert(0,str(RUN))
BEFORE_HASHES, AFTER_HASHES, PIN_ERRORS, TEST_COUNTS = {}, {}, [], None
result = 1

def check_pins(destination):
    for name,(path,expected) in PIN_ROWS.items():
        try:
            info = path.stat() if name == 'interpreter' else path.lstat()
            assert stat.S_ISREG(info.st_mode), 'not regular'
            actual = digest(path)
            destination[name] = actual
            assert actual == expected, 'hash mismatch'
        except BaseException as error:
            PIN_ERRORS.append({'phase':PHASE,'pin':name,'error':str(error)})
    assert not PIN_ERRORS, 'Code/resource/owned pin verification failed'

try:
    check_pins(BEFORE_HASHES)
    import _json
    assert _json.__spec__.origin == 'built-in' and '_json' in sys.builtin_module_names
    assert not hasattr(_json,'__file__')
    assert json.encoder.c_make_encoder is _json.make_encoder
    assert json.encoder.encode_basestring is _json.encode_basestring
    assert pathlib.Path(json.encoder.__file__) == pathlib.Path(CONFIG['json_encoder_path'])
    for owned_name, source_path in CONFIG['source_copies'].items():
        assert (RUN / owned_name).read_bytes() == pathlib.Path(source_path).read_bytes(), owned_name
    PHASE = 'runtime'
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1
    import tempfile, platform
    platform._Processor.from_subprocess = staticmethod(lambda: os.uname().machine)
    tempfile.tempdir = str(RUN)
    import pytest
    result = int(pytest.main(['--noconftest','--rootdir='+str(RUN),'--confcutdir='+str(RUN),'--import-mode=importlib','-c',str(RUN/'pytest.ini'),'-q','-p','no:cacheprovider','--basetemp='+str(RUN/'invented'),'--junitxml='+str(RUN/(label+'.xml')), *[str(RUN/name) for name in CONFIG['selected_tests']]]))
    import xml.etree.ElementTree as ET
    TEST_COUNTS = {key:0 for key in ('tests','failures','errors','skipped')}
    for suite in ET.parse(RUN/(label+'.xml')).getroot().iter('testsuite'):
        for key in TEST_COUNTS: TEST_COUNTS[key] += int(suite.attrib.get(key,'0'))
except BaseException:
    result = 1
    traceback.print_exc()
finally:
    PHASE = 'after'
    try: check_pins(AFTER_HASHES)
    except BaseException: result = 1
    refusal_counts = {v:BLOCKED.count(v) for v in sorted(set(BLOCKED))}
    unclassified = {key:value for key,value in refusal_counts.items() if key not in REFUSAL_LIMITS}
    excess = {key:{'count':value,'ceiling':REFUSAL_LIMITS[key]} for key,value in refusal_counts.items() if key in REFUSAL_LIMITS and value > REFUSAL_LIMITS[key]}
    if TEST_COUNTS != {'tests':CONFIG['expected_tests'],'failures':0,'errors':0,'skipped':0} or BEFORE_HASHES != EXPECTED or AFTER_HASHES != EXPECTED or PIN_ERRORS or unclassified or excess:
        result = 1
    if 'POLICYENGINE_UK_DEFAULT_DATASET' in os.environ: result = 1
    usage = resource.getrusage(resource.RUSAGE_SELF)
    origins = {name:str(module.__file__) for name,module in sorted(sys.modules.items()) if name.startswith('microcosm.') and getattr(module,'__file__',None)}
    receipt = {'label':label,'argv':sys.argv,'result':result,'head':CONFIG['source_head'],'executable':sys.executable,'executable_sha256':digest(EXECUTABLE),'python':sys.version,'wall_seconds':time.monotonic()-START,'cpu_seconds':usage.ru_utime+usage.ru_stime,'peak_rss_bytes':usage.ru_maxrss,'limits':CONFIG['limits'],'test_counts':TEST_COUNTS,'before_hashes':BEFORE_HASHES,'after_hashes':AFTER_HASHES,'expected_pin_count':len(EXPECTED),'pin_errors':PIN_ERRORS,'refusal_counts':refusal_counts,'unclassified_refusals':unclassified,'excess_refusals':excess,'resource_reads_by_phase':{k:sorted(v) for k,v in READS.items()},'allowed_resources':CONFIG['allowed_resources'],'module_origins':origins,'code_reads':sorted(CODE_READS),'symlink_events':SYMLINK_EVENTS,'torch_threads':None if 'torch' not in sys.modules else [sys.modules['torch'].get_num_threads(),sys.modules['torch'].get_num_interop_threads()],'children':0,'network':False,'guard_before_pytest_project_imports':True,'ordinary_imports':True,'configuration_sha256':CONFIG_SHA256,'scope':CONFIG['scope'],'source_pin_scope':'Changed geography slice, selected tests and immediate package roots; not an exhaustive imported-module pin claim','invented_only':True,'release_eligible':False}
    (RUN/(label+'.json')).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({key:receipt[key] for key in ('label','result','wall_seconds','cpu_seconds','peak_rss_bytes','test_counts')}))
raise SystemExit(result)
