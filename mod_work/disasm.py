import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'python_libs'))
import pefile,capstone
p=pefile.PE(str(Path(__file__).parent.parent/'Ekd5扩展功勋版.exe'))
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for arg in sys.argv[1:]:
    v,n=arg.split(':');v=int(v,16);n=int(n,16)
    print('DISASSEMBLY',hex(v))
    for i in md.disasm(p.get_data(v-0x400000,n),v):print(hex(i.address),i.mnemonic,i.op_str)
