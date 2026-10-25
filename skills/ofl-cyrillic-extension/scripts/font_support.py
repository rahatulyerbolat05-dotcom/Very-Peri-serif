"""Small source/identity helpers; no paths or design data from the original project."""
import hashlib
import io
import json
from pathlib import Path
from fontTools.pens.recordingPen import DecomposingRecordingPen

RU='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
KZ='ӘҒҚҢӨҰҮҺІ'
TARGET=RU+KZ+RU.lower()+KZ.lower()
CONTROL='HINOAEVWXOnopbdqgaecxmvwyzfilru'
PROOF_TEXT='''н о п и м л д ж з я
Жизнь · яркая · чаша · дождь · шёпот · тишина
Қазақ тілі: жаңбыр, үміт, ұлы, өмір, ғылым, әңгіме, ілім, қаһарман
УҮҰ уүұ · НҢ нң · КҚ кқ · ОӨ оө · ГҒ гғ · ӘәҺһІі
о́ я́ ы́ э́ ю́ ә́ ү́ і́ ё́ й́ · О́ Я́ Ә́ Ү́ І́ Ё́ Й́
office affine AVATAR Wa To · 12 500,00 ₸ · «Цена» № 57
'''


def sha(value):
    if isinstance(value,(str,Path)):value=Path(value).read_bytes()
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    def default(obj):
        if isinstance(obj,bytes):return {'bytes_hex':obj.hex()}
        raise TypeError(type(obj).__name__)
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),default=default).encode()


def digest(value):return sha(encoded(value))


def glyph_signature(font,name):
    gs=font.getGlyphSet();pen=DecomposingRecordingPen(gs,skipMissingComponents=False);gs[name].draw(pen)
    result={'path':digest(pen.value),'hmtx':list(font['hmtx'][name])}
    if 'glyf' in font:
        result['compiled_outline_and_hints']=sha(font['glyf'][name].compile(font['glyf']))
    elif 'CFF ' in font:
        cs=font['CFF '].cff.topDictIndex[0].CharStrings[name];cs.decompile()
        result['charstring_program']=digest(cs.program)
    return result


def cff_hint_environment(font):
    if 'CFF ' not in font:return None
    cff=font['CFF '].cff
    def subr(sub):
        if sub.bytecode is None:sub.compile()
        return sha(sub.bytecode)
    def private(p):
        return {'values':{k:v for k,v in p.rawDict.items() if k!='Subrs'},
                'subrs':[subr(s) for s in getattr(p,'Subrs',[])]}
    top=cff.topDictIndex[0]
    return {'global_subrs':[subr(s) for s in cff.GlobalSubrs],
            'private':private(top.Private) if hasattr(top,'Private') else None,
            'fd_private':[private(fd.Private) for fd in getattr(top,'FDArray',[])]}


def sfnt_bytes(font):
    """HarfBuzz may not decode WOFF2; serialize a transient sfnt, never the source."""
    import copy
    f=copy.deepcopy(font);f.flavor=None;f.recalcTimestamp=False
    data=io.BytesIO();f.save(data);return data.getvalue()


def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
