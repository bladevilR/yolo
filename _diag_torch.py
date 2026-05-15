import faulthandler, sys
print('before', flush=True)
faulthandler.dump_traceback_later(20, repeat=False)
import torch
print('after', torch.__version__, flush=True)
