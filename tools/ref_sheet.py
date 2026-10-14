import sys
from PIL import Image, ImageDraw, ImageFont
S=None; fontpath=sys.argv[1]; chars=sys.argv[2]; out=sys.argv[3]
SZ=520
f=ImageFont.truetype(fontpath,SZ)
cols=6
rows=(len(chars)+cols-1)//cols
cw,ch=520,760
im=Image.new("RGB",(cols*cw,rows*ch),"white")
d=ImageDraw.Draw(im)
k=SZ/1000
for i,c in enumerate(chars):
    ox=(i%cols)*cw; oy=(i//cols)*ch
    base=oy+620
    for name,val,col in [("base",0,"#e33"),("x",510,"#39f"),("cap",720,"#3a3"),("asc",740,"#aaa"),("desc",-205,"#aaa")]:
        y=base-val*k
        d.line([(ox,y),(ox+cw,y)],fill=col,width=1)
    d.text((ox+60,base),c,font=f,fill="black",anchor="ls")
im.save(out)
