from pathlib import Path
import struct, json, hashlib, re

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'mod_work/test_game'
CID = 646
DONOR = 41
data = bytearray((ROOT / 'Data.e5').read_bytes())
assert data[396+CID*32:399+CID*32] == '空'.encode('gbk')+b'\0'
row = bytearray(data[396+DONOR*32:428+DONOR*32])
row[:13] = '周星宇'.encode('gbk').ljust(13,b'\0')
struct.pack_into('<H', row, 13, 498) # appended face index 505 = 498 + 7
row[17] = 255 # Recruit through the normal script command, not only a faction flag.
row[18:23] = bytes([97,86,76,95,71])
row[23:26] = data[396+4*32+23:396+4*32+26]
row[26] = 15
row[27] = 1
data[396+CID*32:428+CID*32] = row
(OUT / 'Data.e5').write_bytes(data)

# Ls12 uncompressed BMP archive. Preserve all existing image payloads exactly.
face = (ROOT / 'E5/Face.e5').read_bytes()
entries = [struct.unpack_from('>III', face, 272+i*12) for i in range(505)]
assert entries[0][2] == 6336
from PIL import Image
import io
im = Image.open(ROOT / 'mod_work/周星宇/周星宇120.bmp').convert('RGB')
buf=io.BytesIO();im.save(buf,format='BMP');payload=buf.getvalue()
directory = b''.join(struct.pack('>III',a,b,o+12) for a,b,o in entries)
directory += struct.pack('>III',len(payload),len(payload),len(face)+12)
newface=face[:272]+directory+b'\0'*4+face[6336:]+payload
assert newface[6348:6348+43256] == face[6336:6336+43256]
(OUT / 'E5/Face.e5').write_bytes(newface)

exe=bytearray((ROOT/'Ekd5扩展功勋版.exe').read_bytes())
for base in [0xd2800,0xe1000]:
    exe[base+CID*2:base+CID*2+2]=exe[base+DONOR*2:base+DONOR*2+2]
(OUT/'Ekd5扩展功勋版.exe').write_bytes(exe)

def sections(blob):
    """Validate every top-level EEX event length and section boundary."""
    assert blob[:4] == b'EEX\0'
    first = struct.unpack_from('<I',blob,10)[0]
    assert (first-10)%4 == 0
    offsets = list(struct.unpack_from('<'+'I'*((first-10)//4),blob,10))
    assert offsets == sorted(offsets)
    result=[]
    for k,start in enumerate(offsets):
        count=struct.unpack_from('<H',blob,start)[0]
        pos=start+2
        for _ in range(count):
            length=struct.unpack_from('<H',blob,pos)[0]
            result.append((pos,pos+2+length))
            pos+=2+length
        assert pos == (offsets[k+1] if k+1<len(offsets) else len(blob))
    return offsets,result

# No script in the original game mentions the new ID, even as a raw word.
for path in (ROOT/'RS').glob('*.eex'):
    assert struct.pack('<H',CID) not in path.read_bytes(), path

scenario=bytearray((ROOT/'RS/R_00.eex').read_bytes())
offsets,events=sections(scenario)
insert_at=0x45f0
assert scenario[insert_at:insert_at+8] == bytes.fromhex('08 00 2e 00 01 00 06 00')
# Insert outside both difficulty branches, immediately before first preparation.
# 0x3b: recruit; 0x3e: equip with a level-1 basic bow and basic armor.
join=struct.pack('<7H',0x3b,2,CID,0x0e,0,0x3e,0)
equipment=struct.pack('<13H',0x3e,2,CID,0x3b,6,0x49,0,0x3c,57,0x49,0,0x3d,0)
addition=join+equipment
parents=[(a,z) for a,z in events if a+2<=insert_at<z]
assert len(parents)==1
event_start,event_end=parents[0]
struct.pack_into('<H',scenario,event_start,event_end-event_start-2+len(addition))
for i,offset in enumerate(offsets):
    if offset>=insert_at:struct.pack_into('<I',scenario,10+i*4,offset+len(addition))
scenario[insert_at:insert_at]=addition

# First battle originally has only three places, occupied by Liu/Guan/Zhang.
selection_pattern=bytes.fromhex('06 00 2e 00 01 00 04 00 03 00 00 00')
selections=list(re.finditer(re.escape(selection_pattern),scenario))
assert len(selections)==3
for m in selections:struct.pack_into('<I',scenario,m.start()+8,4)
sections(scenario)
assert scenario.count(join)==1
(OUT/'RS/R_00.eex').write_bytes(scenario)

battle=bytearray((ROOT/'RS/S_00.eex').read_bytes())
sections(battle)
placement=bytes.fromhex('4b 00 04 00 03 00 00 00 04 00 00 00 00 00 04 00 00 00 00 00 2b 00 01 00 26 00 00 00')
assert battle.count(placement)==1
pos=battle.index(placement)
struct.pack_into('<I',battle,pos+10,4)
struct.pack_into('<I',battle,pos+16,3)
struct.pack_into('<H',battle,pos+22,2)
sections(battle)
(OUT/'RS/S_00.eex').write_bytes(battle)

# Verify that no original portrait payload was changed by adding the new entry.
for i,(a,b,o) in enumerate(entries):
    na,nb,no=struct.unpack_from('>III',newface,272+i*12)
    assert (a,b)==(na,nb) and face[o:o+b]==newface[no:no+nb]
assert struct.unpack_from('>III',newface,272+505*12)[2]+len(payload)==len(newface)

changed=['Data.e5','Ekd5扩展功勋版.exe','E5/Face.e5','RS/R_00.eex','RS/S_00.eex']
report={'character_id':CID,'portrait_index':505,'stats':list(row[18:23]),
        'class':row[26],'class_name':'短弓骑','equipment':['桦木弓','硬皮甲'],
        'first_battle_position':[4,3],'startup':'新游戏，首次整备前入队',
        'runtime_test':'未进行游戏内验证，由用户测试',
        'checks':['EEX全部段落和事件长度有效','505张原头像逐字节保留','人物编号未被原剧本引用'],
        'files':{name:{'original_sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),
                       'patched_sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
                 for name in changed}}
(ROOT/'mod_work/周星宇/patch_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
